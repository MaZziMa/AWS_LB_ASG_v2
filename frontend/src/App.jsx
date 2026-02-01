import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import CourseList from './components/CourseList';
import StudentList from './components/StudentList';
import EnrollmentList from './components/EnrollmentList';
import KnowledgeBase from './components/KnowledgeBase';
import './index.css';

function Navigation() {
  const location = useLocation();
  
  const navItems = [
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/courses', label: 'Courses', icon: '📚' },
    { path: '/students', label: 'Students', icon: '👨‍🎓' },
    { path: '/enrollments', label: 'Enrollments', icon: '📝' },
    { path: '/kb', label: 'Ask AI', icon: '🤖' }
  ];

  return (
    <nav className="bg-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <h1 className="text-2xl font-bold text-primary">Course Management</h1>
          </div>
          <div className="flex space-x-4">
            {navItems.map(item => (
              <Link
                key={item.path}
                to={item.path}
                className={`px-4 py-2 rounded-lg transition ${
                  location.pathname === item.path
                    ? 'bg-primary text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <span className="mr-2">{item.icon}</span>
                {item.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <main className="max-w-7xl mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/courses" element={<CourseList />} />
            <Route path="/students" element={<StudentList />} />
            <Route path="/enrollments" element={<EnrollmentList />} />
            <Route path="/kb" element={<KnowledgeBase />} />
          </Routes>
        </main>
        <footer className="bg-white border-t mt-12">
          <div className="max-w-7xl mx-auto px-4 py-6 text-center text-gray-500 text-sm">
            <p>Course Management System | AWS Architecture: ALB + ASG + DynamoDB</p>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
