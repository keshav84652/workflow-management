# CPA Copilot - React Frontend

Modern, responsive React frontend for the CPA Copilot tax document processing application.

## 🚀 Features

- **Modern UI/UX**: Built with React 18, TypeScript, and Tailwind CSS
- **Document Upload**: Drag-and-drop interface with progress tracking
- **Real-time Processing**: Live updates during document processing
- **Interactive Results**: Comprehensive analysis and comparison views
- **Workpaper Generation**: PDF workpaper creation with intelligent bookmarks
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Type Safety**: Full TypeScript implementation for better development experience

## 🛠️ Technology Stack

- **Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS with custom theme
- **Routing**: React Router v6
- **HTTP Client**: Axios with interceptors
- **UI Components**: Headless UI + custom components
- **Icons**: Lucide React + Heroicons
- **Animations**: Framer Motion
- **Charts**: Recharts
- **Notifications**: React Hot Toast
- **File Upload**: React Dropzone
- **Build Tool**: Vite
- **Linting**: ESLint + TypeScript ESLint

## 📦 Installation

1. **Navigate to React frontend directory:**
   ```bash
   cd frontend/react
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your configuration:
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   VITE_NODE_ENV=development
   ```

4. **Start development server:**
   ```bash
   npm run dev
   ```

5. **Open in browser:**
   Navigate to `http://localhost:5173`

## 🏗️ Project Structure

```
frontend/react/
├── public/                 # Static assets
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── ui/           # Base UI components
│   │   ├── layout/       # Layout components
│   │   └── forms/        # Form components
│   ├── pages/            # Page components
│   │   ├── Upload.tsx    # Document upload page
│   │   ├── Process.tsx   # Processing page
│   │   ├── Results.tsx   # Results display page
│   │   └── Workpaper.tsx # Workpaper generation page
│   ├── services/         # API services
│   │   └── api.ts        # API client and methods
│   ├── types/            # TypeScript type definitions
│   │   └── index.ts      # Shared type definitions
│   ├── hooks/            # Custom React hooks
│   │   └── useProcessing.ts # Processing state management
│   ├── utils/            # Utility functions
│   │   └── constants.ts  # Application constants
│   ├── App.tsx           # Main application component
│   ├── main.tsx          # Application entry point
│   └── index.css         # Global styles
├── package.json          # Dependencies and scripts
├── vite.config.ts        # Vite configuration
├── tailwind.config.js    # Tailwind CSS configuration
├── tsconfig.json         # TypeScript configuration
└── README.md            # This file
```

## 🔧 Available Scripts

- **`npm run dev`** - Start development server
- **`npm run build`** - Build for production
- **`npm run preview`** - Preview production build
- **`npm run lint`** - Run ESLint
- **`npm run lint:fix`** - Fix ESLint issues
- **`npm run type-check`** - Run TypeScript type checking

## 🎨 Customization

### Tailwind CSS Theme

The application uses a custom Tailwind CSS theme with:
- Custom color palette (primary, secondary, success, warning, error)
- Extended animations and keyframes
- Custom spacing and typography
- Responsive breakpoints

### Environment Variables

Configure the application through environment variables:

```env
# API Configuration
VITE_API_BASE_URL=http://localhost:8000

# File Upload Limits
VITE_MAX_FILE_SIZE=10485760
VITE_ALLOWED_FILE_TYPES=pdf,jpg,jpeg,png,tiff

# Feature Flags
VITE_ENABLE_DEV_TOOLS=true
VITE_ENABLE_ANALYTICS=false
```

## 🔄 API Integration

The frontend communicates with the Python backend through a RESTful API:

- **Upload Endpoint**: `POST /api/upload`
- **Process Endpoint**: `POST /api/process`
- **Results Endpoint**: `GET /api/results`
- **Workpaper Endpoint**: `POST /api/workpaper/generate`

API client includes:
- Automatic token management
- Request/response interceptors
- Error handling with toast notifications
- File upload progress tracking

## 🧪 Development Guidelines

### Component Structure
```tsx
// Component template
import React from 'react'
import { ComponentProps } from '../types'

interface MyComponentProps {
  // Props interface
}

export const MyComponent: React.FC<MyComponentProps> = ({ 
  // Destructured props 
}) => {
  // Component logic
  
  return (
    <div className="component-wrapper">
      {/* JSX content */}
    </div>
  )
}

export default MyComponent
```

### State Management
- Use React hooks for local state
- Custom hooks for shared logic
- Context API for global state (if needed)

### Styling Guidelines
- Use Tailwind CSS utility classes
- Follow mobile-first responsive design
- Maintain consistent spacing and typography
- Use semantic color classes

### Type Safety
- Define interfaces for all props and API responses
- Use TypeScript strict mode
- Avoid `any` types when possible
- Leverage type inference where appropriate

## 🚀 Deployment

### Production Build
```bash
npm run build
```

### Deployment Options
- **Static Hosting**: Netlify, Vercel, GitHub Pages
- **Docker**: Containerized deployment
- **CDN**: Serve built assets from CDN

### Environment Setup
1. Set production environment variables
2. Configure API endpoints
3. Enable production optimizations
4. Set up monitoring and analytics

## 🔧 Troubleshooting

### Common Issues

**API Connection Issues:**
- Verify backend is running on correct port
- Check CORS configuration
- Validate API endpoints in `.env`

**Build Issues:**
- Clear node_modules and reinstall
- Check TypeScript errors
- Verify all dependencies are compatible

**Styling Issues:**
- Rebuild Tailwind CSS
- Check purge configuration
- Verify class names are correct

## 📈 Performance Optimization

- Code splitting with React.lazy()
- Image optimization and lazy loading
- Bundle analysis with Vite
- Caching strategies for API calls
- Progressive Web App features

## 🤝 Contributing

1. Follow existing code style and patterns
2. Add TypeScript types for new features
3. Include responsive design considerations
4. Test across different browsers and devices
5. Update documentation for new features

## 📄 License

This project is proprietary software. All rights reserved.

---

For backend API documentation, see `/backend/README.md`
For overall project documentation, see `/README.md`
