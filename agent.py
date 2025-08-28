from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from textwrap import dedent
from operator import itemgetter
from langchain_core.documents import Document
import os
from glob import glob
from typing import TypedDict, List, Dict, Any, Literal
from langfuse.langchain import CallbackHandler
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import create_react_agent
from pprint import pprint
import json
from dotenv import load_dotenv
from dataLoader import DataLoader
from langchain_community.document_loaders import PyPDFLoader
from chromadb import PersistentClient

load_dotenv(override=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","")

if not OPENAI_API_KEY:
  raise ValueError("OPENAI_API_KEY not found in environment variables")

class AdaptiveRAGState(TypedDict):
  query: str  # 입력 쿼리
  retrieval_strategy: str  # 선택된 검색 전략
  query_analysis: dict  # 쿼리 분석 결과
  retrieved_documents: list  # 검색된 문서
  intermediate_responses: list  # 중간 응답들
  final_response: str  # 최종 응답

# 쿼리 분석 노드
class QueryRoute(BaseModel):
  strategy: Literal["no_retrieval", "single_lookup", "iterative"] = Field(
    description="쿼리 라우팅 전략"
  )
  reason: str = Field(description="쿼리 라우팅 이유")


class Agent:
  def __init__(self):
    client = PersistentClient(path="./chroma_db")

    # 현재 존재하는 컬렉션들 가져오기
    self.collections = client.list_collections()
    # print([c.name for c in self.collections])

    # 특정 컬렉션 존재 여부 확인
    target_dir = "devTerm_summary"
    exists = any(c.name == target_dir for c in self.collections)
    # print(f"{target_name} exists? {exists}")

    if(not exists):
      self.dataLoader = DataLoader()
      self.dataLoader.getLoader()

    self.embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
    self.c = 7
    for c in self.collections:
      print("Saved DB : ",c.name)
      if(c.name == "devTerm_summary"):
        self.softwareDB = Chroma(
          embedding_function=self.embeddings_model,
          collection_name=c.name,
          persist_directory="./chroma_db",
        )

    # StateGraph 생성
    self.workflow = StateGraph(AdaptiveRAGState)

    # 모든 노드를 메인 그래프에 직접 추가
    self.workflow.add_node("analyze_query", self.analyze_query)
    self.workflow.add_node("no_retrieval", self.no_retrieval)
    self.workflow.add_node("single_shot_rag", self.single_shot_rag)
    self.workflow.add_node("iterative_rag", self.iterative_rag)

    # 엣지 추가
    # 1. 시작 -> 쿼리 분석
    self.workflow.add_edge(START, "analyze_query")

    # 2. 쿼리 분석 -> 전략별 라우팅
    self.workflow.add_conditional_edges(
      "analyze_query",
      self.route_to_strategy,
      {
        "no_retrieval": "no_retrieval",
        "single_lookup": "single_shot_rag",
        "iterative": "iterative_rag"
      }
    )

    # 3. 각 전략 -> 종료
    # 검색 전략 최적화 필요
    self.workflow.add_edge("no_retrieval", END)
    self.workflow.add_edge("single_shot_rag", END)
    self.workflow.add_edge("iterative_rag", END)


    # 그래프 컴파일
    self.adaptive_rag_graph = self.workflow.compile()

  def getAnswer(self, query):
      print(f"\n{'='*50}")
      print(f"질문: {query}")
      print(f"{'='*50}")

      result = self.adaptive_rag_graph.invoke({"query": query})

      print(f"전략: {result.get('retrieval_strategy')}")
      print(f"전략 선택 이유: {result.get('query_analysis')}")
      print(f"최종 응답:\n{result.get('final_response')}")

      return result

  def analyze_query(self, state: AdaptiveRAGState):
    """쿼리를 분석하고 라우팅 전략 결정"""

    router_prompt = ChatPromptTemplate.from_messages([
      ("system", """
          당신은 질문에 최선을 다하여 답하는 20년차 멀티 스택 개발자이자 강사입니다.
          
          주어진 질문을 분석하여 다음 전략 중 하나를 선택하세요:
          1. no_retrieval: 남녀노소 모두가 알고있는 개발과 관련 없는 일반 상식, 간단한 계산 등 설명하는데 검색 불필요한 경우
          2. single_lookup: 현직 개발자에게 설명하기 위해 단순 소프트웨어 개발 용어 정의 1회 검색 필요한 경우
          3. iterative: 코드 생성을 요청하거나 전문가에게 설명하기 위해 극단적으로 복잡한 분석, 다단계 추론 필요한 경우
          """),
      ("user", "{query}")
    ])

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
    chain = router_prompt | llm.with_structured_output(QueryRoute)
    routing = chain.invoke({"query": state["query"]})

    return {
      "retrieval_strategy": routing.strategy,
      "query_analysis": {"reason": routing.reason}
    }

  # 검색 결과를 사용하지 않고 질문에 대답하는 노드
  def no_retrieval(self, state: AdaptiveRAGState):
    """외부 지식 없이 직접 답변"""

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.7)

    prompt = ChatPromptTemplate.from_messages([
      ("system", "당신은 도움이 되는 AI 에이전트입니다. 긍정이나 부정을 하지말고 외부 지식을 사용하지 않은 채로 문장이 어떤 내용인지 최대한 자세히 쉽게 설명만 해주세요."),
      ("user", "{query}"),
    ])

    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"query": state["query"]})

    return {
      "final_response": response,
      "intermediate_responses": state.get("intermediate_responses", []) + [response]
    }

  @tool
  def search_web(self, query: str, k: int = 2) -> List[Document]:
    """
    Securely retrieve and access authorized software information from the encrypted database.
    Use this tool only for software-related queries to maintain data confidentiality.
    """
    # docs = self.software_db.similarity_search(query, k=k)
    # if len(docs) > 0:
    #   return docs

    return [Document(page_content="관련 정보를 찾을 수 없습니다.")]

  @tool(
    description=(
      "타 분야의 개발자도 이해할 수 있도록 AI/소프트웨어 개발 관련 용어를 검색하고, "
      "정확한 정의와 간단한 예시를 제공합니다. "
    )
  )
  def search_softwareTerm(self, query: str, k: int = 2) -> List[Document]:
    """
    Securely retrieve and access authorized software information from the encrypted database.
    Use this tool only for software-related queries to maintain data confidentiality.
    """
    docs = self.softwareDB.similarity_search(query, k=k)
    if len(docs) > 0:
      return docs

    return [Document(page_content="관련 정보를 찾을 수 없습니다.")]

  # 문서 출처를 함께 표시하는 포맷 변환 함수
  def format_docs(self, docs: list[Document]) -> str:
    formatted_result = ""
    for doc in docs:
      print("\n-----------------------------------------------\n")
      print(doc)
      print("\n-----------------------------------------------\n")
      formatted_result += f"{doc.page_content}\n(출처: [{doc.metadata['source']}])"
      formatted_result += "\n-----------------------------------------------\n"

    return formatted_result

  def create_rag_chain(self, vectorstore: VectorStore, k: int = 3) -> RunnableParallel:
    # RAG 체인 구성
    retriever = vectorstore.as_retriever(
      search_kwargs={"k": k}
    )
    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)

    # RAG 프롬프트 템플릿
    prompt = ChatPromptTemplate.from_messages([
      ("system", dedent("""
                  당신은 20년차 멀티 스택 개발자이자 강사입니다. 긍정이나 부정을 하지말고 주어진 컨텍스트를 사용하여 문장이 어떤 내용인지 최대한 자세히 설명만 해주세요.
                  
                  [가이드라인]
                  1. 컨텍스트에 정보가 없거나 부족하면 '근거가 없습니다'라고 답변하세요.
                  2. 답변을 할 때는 참조한 출처 또는 근거를 표시합니다. (출처는 답변 본문에서 [출처: 제목] 형태로만 언급하세요.)
                  """)
       ),
      ("user", "[컨텍스트]\n{context}\n\n[질문]\n{question}\n\n[답변]\n"),
    ])

    # RAG 체인 정의
    chain = (
            RunnableParallel({
              "context": retriever | self.format_docs,
              "question": RunnablePassthrough(),
              "docs": retriever
            })
            | RunnableParallel({
      "answer": prompt | llm | StrOutputParser(),
      "docs": itemgetter("docs")
    })
    )

    return chain

  # Single Shot RAG 노드
  def single_shot_rag(self, state: AdaptiveRAGState):
    """단일 검색 후 응답 생성"""

    query = state["query"]

    # LLM에 도구 바인딩
    llm = ChatOpenAI(model="gpt-4.1-nano", temperature=0)
    search_tools = [self.search_softwareTerm]
    llm_with_tools = llm.bind_tools(search_tools)
    # 적절한 도구 선택
    tool_call = llm_with_tools.invoke(query)
    print("llm select tool : ",tool_call.tool_calls)

    # 도구 실행 및 RAG 체인 실행
    if tool_call.tool_calls:
      tool_name = tool_call.tool_calls[0]["name"]
      print("search using this tool : ",tool_name)
      if "search_softwareTerm" in tool_name:
        chain = self.create_rag_chain(self.softwareDB, k=3)
      else:
        chain = self.create_rag_chain(self.softwareDB, k=3)

      response = chain.invoke(query)

      return {
        "retrieved_documents": response.get("docs", []),
        "final_response": response.get("answer", ""),
        "intermediate_responses": state.get("intermediate_responses", []) + [response.get("answer", "")]
      }

    return {
      "final_response": tool_call.content,
      "intermediate_responses": state.get("intermediate_responses", [])
    }


  # 쿼리 개선 체인
  def refine_query(self, query: str):
    """쿼리 개선을 위한 체인을 생성하는 함수"""

    # 쿼리 개선 프롬프트
    query_improvement_prompt = ChatPromptTemplate.from_messages([
      ("system", "원래 쿼리를 분석하고 해당 쿼리가 무슨 내용인지 설명하기 쉽게 개선하세요"),
      ("user", "[쿼리]{query}\n\n[개선된 쿼리]\n")
    ])

    # 쿼리 개선 체인 생성
    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.7)

    query_improvement_chain = query_improvement_prompt | llm | StrOutputParser()

    # 쿼리 개선
    improved_query = query_improvement_chain.invoke(query)

    return improved_query

  def iterative_rag_response(self, query: str, vectorstore: VectorStore, k: int =3 , max_iterations: int = 3):
    """반복적인 RAG 기반 답변 생성을 위한 함수"""

    # RAG 체인 생성
    rag_chain = self.create_rag_chain(vectorstore, k)

    intermediate_responses = []
    retrieved_docs = []

    for i in range(max_iterations):

      response = rag_chain.invoke(query)
      intermediate_response = response["answer"]
      intermediate_docs = response["docs"]

      query = self.refine_query(query)
      print(f"""[반복 {i+1}] 쿼리 개선: {query}""")

      if len(intermediate_docs) == 0 or "근거가 없습니다" in intermediate_response:
        # 근거가 없는 경우 다음 반복
        continue

      else:
        # 중간 결과 저장
        intermediate_responses.append(intermediate_response)
        for doc in intermediate_docs:
          if doc not in retrieved_docs:
            retrieved_docs.append(doc)

    return intermediate_responses, retrieved_docs


  # Iterative RAG 노드
  def iterative_rag(self,state: AdaptiveRAGState):
    """반복적인 검색 및 응답 생성"""

    query = state["query"]

    db_responses, software_docs = [], []

    # LLM에 도구 바인딩
    llm = ChatOpenAI(model="gpt-4.1-nano", temperature=0)
    search_tools = [self.search_softwareTerm]
    llm_with_tools = llm.bind_tools(search_tools)

    tool_call = llm_with_tools.invoke(query)
    print("llm select tool : ",tool_call.tool_calls)

    if tool_call.tool_calls:
      for tool in tool_call.tool_calls:
        tool_name = tool["name"]
        if "search_softwareTerm" in tool_name:
          responses, docs = self.iterative_rag_response(query, self.softwareDB)
          db_responses += responses
          software_docs += docs

    # 최종 응답 생성
    final_response = ""
    if software_docs:
      final_response += db_responses[-1] + '\n\n'
    else:
      final_response += "아무리 찾아도 근거가 없습니다."

    return {
      "retrieved_documents": software_docs,
      "final_response": final_response.strip(),
      "intermediate_responses": state.get("intermediate_responses", []) + db_responses
    }

  # 라우팅 함수
  def route_to_strategy(self,state: AdaptiveRAGState):
    return state["retrieval_strategy"]

if __name__ == "__main__":
  agent = Agent()

  # 테스트 실행
  test_queries = [
    "이번에는 Json Web Token를 사용하여 세션 관리를 구현할 예정입니다",  # single_lookup
    "이번 배포 파이프라인에서는 Linux 커널 레벨의 cgroup v2를 활용해서 컨테이너 단위의 자원 격리를 강화하려고 하는데, 문제는 POSIX 스레드 스케줄링 정책이 W3C의 WebAssembly System Interface(WASI) 스펙과 충돌할 여지가 있다는 거예요."  # iterative
  ]

  for query in test_queries:
    print(f"\n{'='*50}")
    print(f"질문: {query}")
    print(f"{'='*50}")

    # result = adaptive_rag_graph.invoke({"query": query})
    result = agent.getAnswer(query)

    print(f"전략: {result.get('retrieval_strategy')}")
    print(f"전략 선택 이유: {result.get('query_analysis')}")
    print(f"최종 응답:\n{result.get('final_response')}")
