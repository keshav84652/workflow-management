# Collaboration Feature Deep Dive: OpenProject

This document provides a detailed analysis of how OpenProject implements its key collaboration features, based on a review of its source code.

## 1. Comments

Comments are a fundamental collaboration feature in OpenProject, and they are implemented in a way that is both powerful and flexible.

### 1.1. Data Model

The `Comment` model is the heart of the commenting system. It is a polymorphic model, which means that it can be associated with any other model in the application. This is achieved through the `commented` association, which is defined as a `belongs_to` association with the `polymorphic: true` option.

```ruby
# app/models/comment.rb
class Comment < ApplicationRecord
  belongs_to :commented, polymorphic: true, counter_cache: true
  belongs_to :author, class_name: 'User', foreign_key: 'author_id'

  validates :commented, :author, :comments, presence: true

  # ...
end
```

This polymorphic design is what allows comments to be attached to a variety of different objects, such as news items, work packages, and wiki pages.

### 1.2. Business Logic

The business logic for comments is spread across a number of different files, including the `Comment` model, the `CommentsController`, and the various models that can be commented on.

*   **`Comment` model**: The `Comment` model contains the core business logic for comments, such as validation and callbacks.
*   **`CommentsController`**: The `CommentsController` is responsible for handling the HTTP requests for creating, reading, updating, and deleting comments.
*   **Commentable models**: The models that can be commented on (e.g., `News`, `WorkPackage`) include the `acts_as_commentable` concern, which adds the necessary associations and methods for commenting.

### 1.3. Permissions

OpenProject has a rich and fine-grained permission system for comments. The permissions are defined in the `config/initializers/permissions.rb` file, and they include permissions for:

*   Adding comments
*   Editing own comments
*   Editing all comments
*   Deleting own comments
*   Deleting all comments
*   Viewing internal comments
*   Adding internal comments

These permissions can be assigned to roles, and roles can be assigned to users and groups at the project level. This allows for a great deal of flexibility in controlling who can do what with comments.

### 1.4. User Interface

The user interface for comments is implemented using a combination of Rails views and Angular components. The `comments/` directory in the `app/views` directory contains the Rails views for displaying and managing comments, while the `frontend/` directory contains the Angular components for the rich text editor and other UI elements.

## 2. Forums

Forums are another key collaboration feature in OpenProject. They provide a place for users to discuss topics and share information.

### 2.1. Data Model

The data model for forums consists of two main models: `Forum` and `Message`.

*   **`Forum` model**: The `Forum` model represents a forum, which is a container for topics.
*   **`Message` model**: The `Message` model represents a message in a forum. Messages can be either topics or replies. Topics are top-level messages, and replies are messages that are in response to another message.

```ruby
# app/models/forum.rb
class Forum < ApplicationRecord
  belongs_to :project
  has_many :messages, dependent: :destroy

  # ...
end

# app/models/message.rb
class Message < ApplicationRecord
  belongs_to :forum
  belongs_to :author, class_name: 'User', foreign_key: 'author_id'
  belongs_to :parent, class_name: 'Message', foreign_key: 'parent_id', optional: true
  has_many :replies, class_name: 'Message', foreign_key: 'parent_id', dependent: :destroy

  # ...
end
```

### 2.2. Business Logic

The business logic for forums is contained in the `Forum` and `Message` models, as well as the `ForumsController` and `MessagesController`.

*   **`Forum` and `Message` models**: These models contain the core business logic for forums and messages, such as validation and callbacks.
*   **`ForumsController` and `MessagesController`**: These controllers are responsible for handling the HTTP requests for creating, reading, updating, and deleting forums and messages.

### 2.3. Permissions

Like comments, forums have a rich permission system. The permissions are defined in the `config/initializers/permissions.rb` file, and they include permissions for:

*   Managing forums
*   Viewing messages
*   Adding messages
*   Editing messages
*   Deleting messages

These permissions can be assigned to roles, and roles can be assigned to users and groups at the project level.

## 3. Plane: Issues and Cycles

Plane is a modern, feature-rich project management tool with a decoupled architecture. Its core project management functionality is built around the concepts of "issues" and "cycles."

### 3.1. Data Model

The data models for issues and cycles are defined in the `plane/db/models` directory of the `apiserver` service.

*   **`Issue` model**: The `Issue` model is the central model for issues. It has a rich set of fields for tracking the issue's state, priority, and other attributes. It also has a self-referential foreign key, which allows for the creation of sub-issues.
*   **`IssueRelation` model**: This model is used to create relationships between issues, such as "duplicate", "relates_to", and "blocked_by".
*   **`IssueComment` model**: This model is used to store comments on issues.
*   **`Cycle` model**: The `Cycle` model represents a cycle, which is a time-boxed period of work (similar to a sprint in Scrum). It has a `start_date` and `end_date`, as well as a `progress_snapshot` field for storing burn-down chart data.
*   **`CycleIssue` model**: This is a join table that associates issues with cycles.

### 3.2. Business Logic

The business logic for issues and cycles is implemented in the `apiserver` service. The `plane/app/views` directory contains the Django Rest Framework views for the API endpoints, and the `plane/app/serializers` directory contains the serializers for the models.

*   **Issue Creation**: When a new issue is created, the `Issue` model's `save` method is called. This method sets the default state for the issue, calculates the sequence ID, and sets the initial sort order.
*   **Cycle Progress**: The `Cycle` model has a `progress_snapshot` field that is used to store the data for the burn-down chart. This field is updated periodically by a background task.

### 3.3. Real-time Collaboration

Plane uses a dedicated Node.js server running Hocuspocus for real-time collaboration. This server is responsible for managing WebSocket connections and broadcasting changes to connected clients. This is a more scalable approach than handling WebSockets in the main application server, as it offloads the high-concurrency task of managing WebSocket connections to a dedicated service.

## 4. Vikunja: Projects and Tasks

Vikunja is a lightweight and modern to-do list application with a focus on simplicity and ease of use. Its core functionality is built around the concepts of "projects" and "tasks."

### 4.1. Data Model

The data models for projects and tasks are defined in the `pkg/models` directory.

*   **`Project` model**: The `Project` model represents a project, which is a container for tasks. It has a `ParentProjectID` field, which allows for the creation of sub-projects.
*   **`Task` model**: The `Task` model represents a task. It has a rich set of fields, including `DueDate`, `StartDate`, `EndDate`, `RepeatAfter`, and `Priority`. It also has a `RelatedTasks` field, which is used to create relationships between tasks.

### 4.2. Business Logic

The business logic for projects and tasks is contained in the `pkg/models` directory. The `Create` and `Update` methods on the `Project` and `Task` models contain the core business logic for creating and updating these entities.

*   **Task Recurrence**: The `Task` model has a `RepeatAfter` field that is used to define recurrence rules. When a recurring task is marked as done, the `updateDone` function is called to update the due date and other attributes of the task.
*   **Permissions**: Vikunja uses a simple and effective permission system based on the `web.Rights` field. This field is used to control access to projects and tasks, and the permissions are checked in the `web` package.
