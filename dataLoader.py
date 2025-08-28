from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langgraph.types import Send
from pydantic import BaseModel, Field
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.tools import tool
from langchain_core.vectorstores import VectorStore
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from textwrap import dedent
from operator import itemgetter
from langchain_core.documents import Document
import os
from glob import glob
from typing import Annotated, List, Dict, Tuple, Any
from typing_extensions import TypedDict
import operator
from langfuse.langchain import CallbackHandler
from langgraph.graph import StateGraph, END, START
from pprint import pprint
import json
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from docling.document_converter import DocumentConverter
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.accelerator_options import AcceleratorDevice
from docling_core.types.doc import TextItem, TableItem
import pandas as pd
from docling_core.types.doc import TextItem, TableItem
import pandas as pd
import pickle
from chromadb import PersistentClient
from pathlib import Path

load_dotenv(override=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","")

if not OPENAI_API_KEY:
  raise ValueError("OPENAI_API_KEY not found in environment variables")

class SummarizationState(TypedDict):
  contents: List[Document]  # 초기 Document 객체 리스트
  chunks: List[Dict[str, Any]]  # 청크 리스트 (인덱스, 내용, 메타데이터 포함)
  summaries: Annotated[List[Tuple[int, str]], operator.add]  # (인덱스, 요약) 튜플 리스트
  final_summary: str

class DocumentState(TypedDict):
  content: str
  index: int  # 청크의 순서를 나타내는 인덱스
  metadata: Any #metadata

class AdvancedDocProcessor:
  """고급 문서 처리기"""

  def __init__(self, enable_ocr=False, enable_table_structure=True):
    """
    Args:
        enable_ocr: OCR 기능 활성화 (스캔된 문서용)
        enable_table_structure: 테이블 구조 분석 활성화
    """

    # 파이프라인 옵션 설정
    pipeline_options = PdfPipelineOptions()  # PDF 변환을 위한 파이프라인 옵션 (기본값 사용)
    pipeline_options.do_ocr = enable_ocr   # OCR 활성화 여부
    pipeline_options.do_table_structure = enable_table_structure # 테이블 구조 분석 활성화 여부

    # 테이블 구조 분석 세부 설정
    if enable_table_structure:
      pipeline_options.table_structure_options.do_cell_matching = True # 셀 매칭

    # CPU 사용 설정 (GPU가 없는 환경)
    pipeline_options.accelerator_options.device = AcceleratorDevice.CPU

    # DocumentConverter 초기화
    self.converter = DocumentConverter(
      format_options={
        InputFormat.PDF: PdfFormatOption(
          pipeline_options=pipeline_options
        )
      }
    )

    print(f"🔧 처리기 초기화 완료:")
    print(f"   - OCR: {'활성화' if enable_ocr else '비활성화'}")
    print(f"   - 테이블 구조 분석: {'활성화' if enable_table_structure else '비활성화'}")

  def process_pdf(self, pdf_path):
    """PDF 처리"""
    try:
      print(f"처리 시작: {pdf_path}")
      result = self.converter.convert(str(pdf_path))

      if result.status.name in ['SUCCESS', 'PARTIAL_SUCCESS']:
        print(f"처리 완료: {result.status.name}")
        return result.document
      else:
        print(f"처리 실패: {result.status}")
        return None

    except Exception as e:
      print(f"오류 발생: {e}")
      return None

class UnstructuredDataLoader:
  def __init__(self, pdf_path):
    # 기본 설정으로 처리
    # self.basic_processor = AdvancedDocProcessor(
    #   enable_ocr=False,
    #   enable_table_structure=False
    # )
    #
    # # PDF 처리 실행
    # document = self.basic_processor.process_pdf(pdf_path)
    #
    # # 결과 분석
    # markdown = document.export_to_markdown()
    #
    # print(f"- 문서명: {document.name}")
    # print(f"- 텍스트 길이: {len(markdown)}자")
    #
    # # 테이블이 있는지 확인
    # if "| " in markdown or "|--" in markdown:
    #   print("   - 🔍 테이블 구조 감지됨")
    # else:
    #   print("   - 📝 일반 텍스트 문서")
    #
    # save_folder = Path("data/docling_output")
    # save_folder.mkdir(parents=True, exist_ok=True)
    #
    # with open(save_folder / f"{document.name}_table.md", "w", encoding="utf-8") as f:
    #   f.write(markdown)
    #
    # ordered_json = self.convert_document_to_ordered_json(document)
    # print(f"문서 요소를 원본 순서대로 JSON 배열로 변환 완료. 총 {len(ordered_json)}개 요소.")
    # print("================================================")

    # 고급 설정으로 처리
    self.ocr_processor = AdvancedDocProcessor(
      enable_ocr=True,  # OCR 활성화
      enable_table_structure=True # 테이블 구조 분석 활성화
    )

    # PDF 처리 실행
    ocr_document = self.ocr_processor.process_pdf(pdf_path)

    ocr_markdown = ocr_document.export_to_markdown()

    print(f"- 문서명: {ocr_document.name}")
    print(f"- 텍스트 길이: {len(ocr_markdown)}자")

    # 테이블이 있는지 확인
    if "| " in ocr_markdown or "|--" in ocr_markdown:
      print("   - 🔍 테이블 구조 감지됨")
    else:
      print("   - 📝 일반 텍스트 문서")

    ocr_save_folder = Path("data/docling_output")
    ocr_save_folder.mkdir(parents=True, exist_ok=True)

    with open(ocr_save_folder / f"{document.name}_table_ocr.md", "w", encoding="utf-8") as f:
      f.write(ocr_markdown)

    pickle_ordered_json = self.convert_document_to_ordered_json(ocr_document)
    print(f"문서 요소를 원본 순서대로 JSON 배열로 변환 완료. 총 {len(pickle_ordered_json)}개 요소.")

    pickle_save_folder = Path("data/docling_output")
    pickle_save_folder.mkdir(parents=True, exist_ok=True)
    pickle_path = pickle_save_folder / f"{document.name}_analysis_ocr.pkl"

    with open(pickle_path, "wb") as f:
      pickle.dump(pickle_ordered_json, f)

    print(f"pickle 파일로 저장됨: {pickle_path}")


  # DoclingDocument의 텍스트와 테이블 요소를 순서대로 JSON으로 변환
  def convert_document_to_ordered_json(self,document):
    """문서 요소를 원본 순서대로 JSON 배열로 변환 (테이블은 마크다운+딕셔너리 형식)"""
    elements = []

    for item, level in document.iterate_items():
      if isinstance(item, TextItem):
        elements.append({
          "type": "text",
          "content": item.text.replace("\t", " ") or "",
          "page": item.prov[0].page_no if item.prov else None,
          "label": item.label.value if item.label else None,
          "level": level,
          "element": item  # 원본 요소 추가
        })
      elif isinstance(item, TableItem):
        table_content = {}

        try:
          # DataFrame으로 변환
          df = item.export_to_dataframe()

          # 마크다운 형식으로 변환
          markdown_content = df.to_markdown(index=False)  # 인덱스 제외

          # 딕셔너리 형식으로 변환 (여러 옵션 제공)
          dict_content = df.to_dict('records')     # 각 행을 딕셔너리로

          table_content = {
            "markdown": markdown_content,
            "data": dict_content,
            "status": "success"
          }

        except Exception as e:
          # DataFrame 변환이 실패한 경우 대안 시도
          try:
            html_content = item.export_to_html()
            table_content = {
              "html": html_content,
              "status": "html_fallback",
              "error": str(e)
            }
          except Exception as e2:
            table_content = {
              "status": "failed",
              "error": f"DataFrame 변환 실패: {str(e)}, HTML 변환 실패: {str(e2)}"
            }

        elements.append({
          "type": "table",
          "content": table_content,
          "page": item.prov[0].page_no if item.prov else None,
          "level": level,
          "element": item  # 원본 요소 추가
        })

    return elements

localDB = None
first= True
class DataLoader:
  def __init__(self,pdf_path):
    global localDB,first
    self.loader = PyPDFLoader(pdf_path)
    self.collection_name = "devTerm_summary"#pdf_path.split("/")[-1][:-4]
    self.documents = self.loader.load()
    self.embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

    client = PersistentClient(path="./chroma_db")

    self.collections = client.list_collections()
    exists = any(c.name == self.collection_name for c in self.collections)
    print(first)
    if(first):
      localDB = Chroma(
        collection_name=self.collection_name,
        embedding_function=self.embeddings_model,
        persist_directory='./chroma_db',
      )
      first=False

    self.initial_state = {
      "contents": self.documents,
    }
    self.model = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
    # 그래프 구성
    self.builder = StateGraph(SummarizationState)
    self.builder.add_node("split_documents", self.split_documents_tiktoken)
    self.builder.add_node("translate_document", self.translate_document)
    self.builder.add_node("create_final_summary", self.create_final_summary)

    # 엣지 연결
    self.builder.add_edge(START, "split_documents")
    self.builder.add_conditional_edges("split_documents", self.continue_to_summarization, ["summarize_document"])
    self.builder.add_edge("translate_document", "create_final_summary")
    self.builder.add_edge("create_final_summary", END)

    print(f"로드된 페이지 수: {len(self.documents)}")

  def getLoader(self):
    # 그래프 컴파일
    graph = self.builder.compile()

    for step in graph.stream(self.initial_state, stream_mode="values"):
      if "chunks" in step:
        print(f"처리 중인 청크 수: {len(step['chunks'])}")
      if "summaries" in step:
        print(f"현재까지 생성된 요약 수: {len(step['summaries'])}")
      if "final_summary" in step:
        print("최종 요약 생성 중...")
        print(step["final_summary"])  # 최종 요약 출력
      print("-"*100)

      print("최종 상태:")
      print("최종 요약:", step.get("final_summary", "요약이 생성되지 않았습니다."))
      print("전체 청크 수:", len(step.get("chunks", [])))
      print("전체 요약 수:", len(step.get("summaries", [])))
      print("전체 문서 수:", len(step.get("contents", [])))

  def split_documents_tiktoken(self,state: SummarizationState):
    # global localDB
    """토큰 기반으로 문서를 분할"""
    encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4, GPT-3.5에서 주로 사용

    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
      encoding_name="cl100k_base",
      chunk_size=300,   # 토큰 단위
      chunk_overlap=0
    )

    chunks = []
    global_chunk_index = 0

    for doc_index, document in enumerate(state["contents"]):
      # split_texts = splitter.split_text(document.page_content)
      split_chunks = splitter.split_documents([document])

      for text in split_chunks:
        chunks.append({
          "index": global_chunk_index,
          "content": text,
          "source_document": doc_index,
          "source_metadata": document.metadata
        })
        global_chunk_index += 1

      # self.db = Chroma.from_documents(
      #   documents=split_chunks,
      #   embedding=self.embeddings_model,    # OpenAI 임베딩 사용
      #   collection_name=self.collection_name,    # 컬렉션 이름
      #   persist_directory="./chroma_db",
      #   collection_metadata = {'hnsw:space': 'cosine'}, # l2, ip, cosine 중에서 선택
      # )

    return {"chunks": chunks}

  def split_documents_semantic(self,state: SummarizationState):
    """의미 기반으로 문서를 분할"""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    splitter = SemanticChunker(embeddings, breakpoint_threshold_type="gradient")

    chunks = []
    global_chunk_index = 0

    for doc_index, document in enumerate(state["contents"]):
      # print('doc num : ',doc_index)
      split_docs = splitter.split_documents([document])

      for d in split_docs:
        chunks.append({
          "index": global_chunk_index,
          "content": d.page_content,
          "source_document": doc_index,
          "source_metadata": d.metadata
        })
        global_chunk_index += 1
        self.software_db.add_documents(d)
        print('software_db : ',self.software_db.get())

    return {"chunks": chunks}

  def split_documents(self,state: SummarizationState):
    """각 Document를 순서를 유지하며 청크로 분할"""
    chunks = []
    chunk_size = 1000
    global_chunk_index = 0

    # 각 Document를 순차적으로 처리
    for doc_index, document in enumerate(state["contents"]):
      content = document.page_content

      # 해당 문서를 청크로 분할
      for i in range(0, len(content), chunk_size):
        chunk_content = content[i:i + chunk_size]

        # 빈 청크는 스킵
        if chunk_content.strip():
          chunks.append({
            "index": global_chunk_index,
            "content": chunk_content,
            "source_document": doc_index,
            "source_metadata": document.metadata
          })
          global_chunk_index += 1

    return {"chunks": chunks}

  def translate_document(self,state: DocumentState):
    global localDB
    """개별 문서 청크를 한국어로 자연스럽게 번역"""
    prompt = f"""다음 텍스트 중 개발 용어 및 정의만 한국어로 번역하고 개발자가 이해하기 좋게 설명을 추가해주세요 개발과 관련 없는 부분은 무시해주세요:
      
      {state['content']}
      """

    try:
      response = self.model.invoke(prompt)
      summary = response.content
      if(localDB != None):
        print('chunk summary: ',summary)
        print('\n-------------------------------------------------\n')
        print(' original / ',state['metadata'])#state['content'],' / ',
        localDB.add_documents(
          [
            Document(
              page_content=summary,
              metadata={"original": state['content'], "source":state['metadata']}
            )
          ]
        )
        print('db name : ',self.collection_name, " len : " ,localDB._collection.count())
    except Exception as e:
      summary = f"요약 생성 중 오류 발생: {str(e)}"

    # 순서 정보와 함께 요약 반환
    return {"summaries": [(state["index"], summary)]}

  def continue_to_summarization(self,state: SummarizationState):
    """각 청크를 병렬로 요약하도록 Send 작업 생성"""
    return [
      Send("summarize_document", {
        "content": chunk["content"],
        "index": chunk["index"],
        "metadata": chunk["source_metadata"]
      })
      for chunk in state["chunks"]
    ]

  def create_final_summary(self,state: SummarizationState):
    """순서를 유지하며 최종 요약 생성"""
    # 인덱스별로 요약을 정렬
    sorted_summaries = sorted(state["summaries"], key=lambda x: x[0])

    # 순서대로 요약들을 결합
    ordered_summaries = [summary for _, summary in sorted_summaries]
    combined_summaries = "\n\n".join(ordered_summaries)

    prompt = f"""다음은 문서를 청크별로 번역한 내용들입니다. 
      이들을 종합하여 하나의 포괄적이고 일관성 있는 최종 요약을 작성해주세요.
      원본 문서의 순서와 흐름을 유지하면서 핵심 내용을 간결하게 정리해주세요:
      
      {combined_summaries}
      
      최종 요약:
      """

    try:
      response = self.model.invoke(prompt)
      final_summary = response.content
      # DB에 최종 요약 저장
    except Exception as e:
      final_summary = f"최종 요약 생성 중 오류 발생: {str(e)}"

    return {"final_summary": final_summary}

if __name__ == "__main__":
  root_dir = "data/Dev"

  for dirpath, dirnames, filenames in os.walk(root_dir):
    for filename in filenames:
      print(f"  파일: {filename}")
      pdf_path = root_dir + "/" + filename
      db = DataLoader(pdf_path)
      db.getLoader()