# Feature Implementation Deep Dive: Focalboard

This document provides a detailed analysis of how Focalboard implements its key features, based on a review of its source code.

## 1. Board and Card Management

Focalboard's core functionality revolves around boards and cards. The implementation of these features is a good example of a clean, monolithic architecture.

*   **Backend (`server/` directory)**:
    *   **Data Models (`model/`)**: The `Board` and `Card` structs in the `model` directory define the data structures for these entities. They are simple Go structs with JSON tags for serialization.
    *   **API Endpoints (`api/`)**: The `api` directory contains the HTTP handlers for the board and card APIs. For example, `api/boards.go` defines the RESTful endpoints for creating, reading, updating, and deleting boards.
    *   **Application Logic (`app/`)**: The `app` directory contains the core business logic for managing boards and cards. For example, `app/boards.go` contains the `CreateBoard` and `GetBoard` functions, which are called by the API handlers.
    *   **Database Access (`store/`)**: The `store` directory abstracts the database interactions. The `sqlstore` implementation uses the `gorp` library to map Go structs to SQL tables.

*   **Frontend (`webapp/` directory)**:
    *   **React Components (`src/components/`)**: The frontend is built with React. The `Board` and `Card` components are responsible for rendering the boards and cards.
    *   **State Management (`src/store/`)**: Redux is used for state management. The `boards` and `cards` reducers manage the state of the boards and cards in the application.
    *   **API Client (`src/services/`)**: The frontend communicates with the backend via a RESTful API. The `boards` and `cards` services in the `src/services` directory contain the logic for making API calls.

## 2. Real-time Collaboration

Focalboard uses WebSockets for real-time collaboration. When a user makes a change to a board, the backend sends a message to all connected clients, who then update their local state.

*   **Backend (`server/ws/`)**: The `ws` directory contains the WebSocket server. The `hub` is responsible for managing the WebSocket connections and broadcasting messages to the clients.
*   **Frontend (`src/ws/`)**: The frontend establishes a WebSocket connection with the server when the application loads. The `ws` service in the `src/ws` directory contains the logic for handling incoming WebSocket messages and updating the Redux store.

## 3. Desktop Application

Focalboard also provides a standalone desktop application for Windows, macOS, and Linux. The desktop application is built using Electron.

*   **Electron Shell (`main.js`)**: The `main.js` file is the entry point for the Electron application. It creates a browser window and loads the web application.
*   **Packaged Server**: The desktop application packages the Go server and runs it as a child process. This allows the desktop application to work offline and store data locally in a SQLite database.
