# Course Management Frontend

React + Vite frontend for Course Management System.

## Features

- 📊 Dashboard with health monitoring
- 📚 Course management (CRUD)
- 👨‍🎓 Student management
- 📝 Enrollment tracking with progress
- 🎨 Tailwind CSS styling
- 🔄 Real-time API integration with AWS ALB

## Quick Start

### Install Dependencies
```bash
cd frontend
npm install
```

### Development Server
```bash
npm run dev
```
Access at: http://localhost:3000

### Build for Production
```bash
npm run build
```

## Project Structure
```
frontend/
├── src/
│   ├── components/      # React components
│   │   ├── Dashboard.jsx
│   │   ├── CourseList.jsx
│   │   ├── StudentList.jsx
│   │   └── EnrollmentList.jsx
│   ├── services/        # API service layer
│   │   └── api.js
│   ├── App.jsx          # Main app with routing
│   ├── main.jsx         # Entry point
│   └── index.css        # Global styles
├── index.html
├── vite.config.js       # Vite config with proxy
├── tailwind.config.js
└── package.json
```

## API Configuration

The app uses Vite proxy to forward `/api` requests to AWS ALB:
- Development: Proxy configured in `vite.config.js`
- Production: Set `VITE_API_URL` environment variable

## Environment Variables

Create `.env` file:
```
VITE_API_URL=http://your-alb-dns-name.amazonaws.com
```

## Components

### Dashboard
- System health check
- Quick start guide
- Architecture overview

### CourseList
- View all courses in card grid
- Create new courses
- Delete courses
- Real-time CRUD operations

### StudentList
- Table view of all students
- Add new students
- Email and phone management

### EnrollmentList
- Enrollment tracking
- Progress indicators
- Student-course relationships
- Status badges (Completed/In Progress)

## Technologies

- **React 18** - UI library
- **Vite** - Build tool
- **React Router** - Client-side routing
- **Axios** - HTTP client
- **Tailwind CSS** - Utility-first CSS

## Development Tips

1. **Hot Reload**: Changes auto-reload in dev mode
2. **API Errors**: Check browser console for API issues
3. **CORS**: Handled by Vite proxy in development
4. **Styling**: Use Tailwind utility classes

## Deployment

### Static Hosting (S3 + CloudFront)
```bash
npm run build
# Upload dist/ folder to S3
# Configure CloudFront with proper origins
```

### Docker
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

## Troubleshooting

**API not connecting:**
- Verify ALB URL in `vite.config.js`
- Check CORS settings on backend
- Ensure ALB security group allows traffic

**Build errors:**
- Clear node_modules: `rm -rf node_modules && npm install`
- Update dependencies: `npm update`

**Styling issues:**
- Rebuild Tailwind: `npm run build`
- Check for conflicting CSS
