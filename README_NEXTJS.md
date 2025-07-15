# CPA WorkflowPilot - Next.js Migration

This is the modern Next.js version of CPA WorkflowPilot, migrating from the original Flask application to a modern React-based frontend with shadcn/ui components.

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ 
- npm or yarn
- The original Flask backend running on port 5002

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

## 📁 Project Structure

```
├── app/                    # Next.js 13+ App Router
│   ├── dashboard/         # Dashboard pages and layout
│   ├── login/            # Authentication pages
│   ├── globals.css       # Global styles with Tailwind
│   ├── layout.tsx        # Root layout
│   └── page.tsx          # Landing page
├── components/
│   └── ui/               # shadcn/ui components
├── lib/
│   └── utils.ts          # Utility functions
└── public/               # Static assets
```

## 🎨 Design System

### Technologies Used
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - High-quality React components
- **Radix UI** - Unstyled, accessible UI primitives
- **Lucide React** - Beautiful icons

### Color Palette
- **Primary**: Blue gradient (#1e3a8a to #3b82f6)
- **Secondary**: Green accent (#10b981)
- **Warning**: Amber (#f59e0b)
- **Danger**: Red (#ef4444)

## 🔄 Migration Progress

### ✅ Completed
- [x] Project setup with Next.js 14
- [x] Tailwind CSS configuration
- [x] shadcn/ui component library setup
- [x] Landing page with modern design
- [x] Dashboard layout with responsive sidebar
- [x] Dashboard overview page
- [x] Projects page with grid layout
- [x] Login page with glassmorphism design
- [x] Basic routing structure

### 🚧 In Progress
- [ ] Tasks management page
- [ ] Clients management page
- [ ] Documents page
- [ ] Calendar integration
- [ ] API integration with Flask backend
- [ ] Authentication system
- [ ] Form handling with react-hook-form

### 📋 Todo
- [ ] Settings page
- [ ] User management
- [ ] Real-time updates
- [ ] Mobile optimization
- [ ] Performance optimization
- [ ] Testing setup
- [ ] Deployment configuration

## 🔌 Backend Integration

The Next.js app is configured to proxy API requests to the Flask backend:
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5002/api/*`

API calls are automatically proxied through Next.js configuration.

## 🎯 Key Features Migrated

1. **Modern Landing Page**: Glass morphism design with gradient backgrounds
2. **Responsive Dashboard**: Collapsible sidebar with navigation
3. **Project Management**: Card-based layout with progress tracking
4. **Component Library**: Reusable shadcn/ui components
5. **Type Safety**: Full TypeScript implementation

## 🚀 Development Commands

```bash
# Development server
npm run dev

# Production build
npm run build

# Start production server
npm start

# Linting
npm run lint
```

## 📱 Responsive Design

The application is fully responsive with:
- Mobile-first approach
- Collapsible sidebar on mobile
- Adaptive grid layouts
- Touch-friendly interactions

## 🎨 Component Examples

### Button Usage
```tsx
import { Button } from '@/components/ui/button'

<Button variant="default" size="lg">
  Primary Action
</Button>
```

### Card Usage
```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

<Card>
  <CardHeader>
    <CardTitle>Card Title</CardTitle>
  </CardHeader>
  <CardContent>
    Card content goes here
  </CardContent>
</Card>
```

## 🔄 Next Steps

1. **Complete Core Pages**: Finish migrating all main dashboard pages
2. **API Integration**: Connect with Flask backend APIs
3. **Authentication**: Implement JWT-based auth
4. **Real-time Features**: Add WebSocket support
5. **Performance**: Optimize bundle size and loading
6. **Testing**: Add comprehensive test suite

This migration provides a modern, maintainable, and scalable frontend while preserving all the functionality of the original Flask application.