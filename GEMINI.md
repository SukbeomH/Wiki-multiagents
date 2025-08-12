# GEMINI.md

## Project Overview

This project is a Streamlit-based multi-page web application that functions as a collaborative multi-agent system for economic analysis. It leverages LangChain and LangGraph to create a system of AI agents with different specializations, including a Supervisor, a Researcher, and an Analyst. The application provides in-depth analysis of economic questions by combining a sophisticated RAG (Retrieval-Augmented Generation) pipeline with real-time web search capabilities.

The core technologies used in this project are:

*   **AI Agent Framework:** LangChain, LangGraph
*   **LLM:** Azure OpenAI Service (GPT-4o)
*   **UI/UX:** Streamlit
*   **RAG:** FAISS VectorStore, MultiQueryRetriever, ContextualCompressionRetriever
*   **Web Search:** DuckDuckGo Search

The project is structured in a modular way, with separate directories for components, core logic, and utilities. This makes the codebase easy to maintain and extend.

## Building and Running

To build and run the project, follow these steps:

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set up Environment Variables:**
    Copy the `.env.example` file to `.env` and fill in the required values for the Azure OpenAI Service.

3.  **Run the Application:**
    ```bash
    streamlit run app.py
    ```

## Development Conventions

The project follows a set of development conventions to ensure code quality and consistency:

*   **Modular Architecture:** The code is organized into modules with specific responsibilities, such as `core` for business logic, `components` for UI elements, and `utils` for helper functions.
*   **State Management:** The application uses Streamlit's session state to manage the application's state, with a dedicated `StateManager` class to centralize state management.
*   **Logging:** The project uses the standard Python `logging` module for logging, with different log levels for different types of information.
*   **Environment Variables:** The application uses a `.env` file to manage environment variables, with a dedicated `EnvironmentValidator` class to validate the environment variables.
*   **RAG Pipeline:** The project uses a sophisticated RAG pipeline with a FAISS vector store and a multi-query retriever to retrieve relevant information from a collection of documents.
*   **Multi-Agent System:** The project uses a multi-agent system with a Supervisor, a Researcher, and an Analyst to perform economic analysis. The agents are implemented using LangGraph.
