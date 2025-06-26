# Focalboard Features

Based on the README.md and source code analysis, Focalboard has the following features:

### High-Level Features

*   **Project Management**: An alternative to Trello, Notion, and Asana for defining, organizing, tracking, and managing work.
*   **Multiple Editions**:
    *   **Personal Desktop**: A standalone, single-user desktop app for macOS, Windows, and Linux.
    *   **Personal Server**: A standalone, multi-user server.
*   **API**: Provides an API for integration.
*   **Multilingual**: Supports multiple languages.
*   **Self-hosted**: Can be self-hosted.
*   **Docker Support**: Can be run using Docker.

### Detailed Features

*   **Boards**:
    *   Create, get, patch, and delete boards.
    *   Duplicate boards, including as templates.
    *   Get boards for a user and team.
    *   Add and remove members from boards, with different roles (admin, member).
    *   Search for boards.
    *   Boards can be linked to Mattermost channels.
    *   Boards have types (public, private).
    *   Boards can be organized into categories.
*   **Cards**:
    *   Create, get, and patch cards.
    *   Cards are a type of "block".
    *   Cards belong to a board.
*   **Teams**:
    *   Get, create, and update teams.
    *   Get teams for a user.
    *   Users can have access to multiple teams.
