import React, { useState, useEffect } from 'react';
import { coursesAPI } from '../services/api';

export default function CourseList() {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const PAGE_SIZE = 20;
  const [cursor, setCursor] = useState(null);
  const [nextCursor, setNextCursor] = useState(null);
  const [cursorStack, setCursorStack] = useState([]);
  const [formData, setFormData] = useState({
    course_id: '',
    title: '',
    description: '',
    instructor: '',
    duration_hours: '',
    price: '',
    category: ''
  });

  useEffect(() => {
    fetchCourses(null);
  }, []);

  const fetchCourses = async (cursorOverride) => {
    try {
      setLoading(true);
      const effectiveCursor = cursorOverride !== undefined ? cursorOverride : cursor;
      const params = {
        limit: PAGE_SIZE,
      };

      const trimmed = searchQuery.trim();
      if (trimmed) params.q = trimmed;
      if (effectiveCursor) params.cursor = effectiveCursor;

      const response = await coursesAPI.getAll(params);
      setCourses(response.data.courses || []);
      setNextCursor(response.data.next_cursor || null);
      setError(null);
    } catch (err) {
      setError('Failed to load courses: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    setCursorStack([]);
    setCursor(null);
    await fetchCourses(null);
  };

  const handleNextPage = async () => {
    if (!nextCursor) return;
    setCursorStack((prev) => [...prev, cursor]);
    setCursor(nextCursor);
    await fetchCourses(nextCursor);
  };

  const handlePrevPage = async () => {
    if (cursorStack.length === 0) return;
    const newStack = [...cursorStack];
    const prevCursor = newStack.pop() || null;
    setCursorStack(newStack);
    setCursor(prevCursor);
    await fetchCourses(prevCursor);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await coursesAPI.create({
        ...formData,
        duration_hours: parseInt(formData.duration_hours),
        price: parseFloat(formData.price)
      });
      setShowForm(false);
      setFormData({
        course_id: '',
        title: '',
        description: '',
        instructor: '',
        duration_hours: '',
        price: '',
        category: ''
      });
      fetchCourses();
    } catch (err) {
      alert('Failed to create course: ' + err.message);
    }
  };

  const handleDelete = async (courseId) => {
    if (!window.confirm('Are you sure you want to delete this course?')) return;
    try {
      await coursesAPI.delete(courseId);
      fetchCourses();
    } catch (err) {
      alert('Failed to delete course: ' + err.message);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading courses...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Courses</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-primary text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition"
        >
          {showForm ? 'Cancel' : '+ Add Course'}
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <form onSubmit={handleSearch} className="bg-white p-4 rounded-lg shadow-md mb-6">
        <div className="flex flex-col md:flex-row md:items-center gap-3">
          <input
            type="text"
            placeholder="Search by Title, Course ID, Instructor, Category"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="border px-3 py-2 rounded w-full"
          />
          <button
            type="submit"
            className="bg-primary text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition"
          >
            Search
          </button>
        </div>
        <div className="mt-3 flex items-center justify-between">
          <div className="text-sm text-gray-600">Showing {courses.length} result(s) (max {PAGE_SIZE} per page)</div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handlePrevPage}
              disabled={cursorStack.length === 0}
              className="px-3 py-2 rounded border disabled:opacity-50"
            >
              Prev
            </button>
            <button
              type="button"
              onClick={handleNextPage}
              disabled={!nextCursor}
              className="px-3 py-2 rounded border disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </form>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input
              type="text"
              placeholder="Course ID (e.g., CS101)"
              value={formData.course_id}
              onChange={(e) => setFormData({ ...formData, course_id: e.target.value })}
              className="border px-3 py-2 rounded"
              required
            />
            <input
              type="text"
              placeholder="Title"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="border px-3 py-2 rounded"
              required
            />
            <input
              type="text"
              placeholder="Instructor"
              value={formData.instructor}
              onChange={(e) => setFormData({ ...formData, instructor: e.target.value })}
              className="border px-3 py-2 rounded"
              required
            />
            <input
              type="text"
              placeholder="Category"
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              className="border px-3 py-2 rounded"
              required
            />
            <input
              type="number"
              placeholder="Duration (hours)"
              value={formData.duration_hours}
              onChange={(e) => setFormData({ ...formData, duration_hours: e.target.value })}
              className="border px-3 py-2 rounded"
              required
            />
            <input
              type="number"
              step="0.01"
              placeholder="Price"
              value={formData.price}
              onChange={(e) => setFormData({ ...formData, price: e.target.value })}
              className="border px-3 py-2 rounded"
              required
            />
            <textarea
              placeholder="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="border px-3 py-2 rounded md:col-span-2"
              rows="3"
              required
            />
          </div>
          <button
            type="submit"
            className="mt-4 bg-secondary text-white px-6 py-2 rounded hover:bg-green-600 transition"
          >
            Create Course
          </button>
        </form>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {courses.map((course) => (
          <div key={course.course_id} className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition">
            <div className="flex justify-between items-start mb-3">
              <h3 className="text-xl font-semibold text-gray-800">{course.title}</h3>
              <button
                onClick={() => handleDelete(course.course_id)}
                className="text-red-500 hover:text-red-700 text-sm"
              >
                Delete
              </button>
            </div>
            <p className="text-sm text-gray-600 mb-2">ID: {course.course_id}</p>
            <p className="text-gray-700 mb-3">{course.description}</p>
            <div className="space-y-1 text-sm">
              <p><span className="font-medium">Instructor:</span> {course.instructor}</p>
              <p><span className="font-medium">Category:</span> {course.category}</p>
              <p><span className="font-medium">Duration:</span> {course.duration_hours} hours</p>
              <p><span className="font-medium text-primary">Price:</span> ${course.price}</p>
            </div>
          </div>
        ))}
      </div>

      {courses.length === 0 && !loading && (
        <div className="text-center py-12 text-gray-500">
          No courses found. Add your first course to get started!
        </div>
      )}
    </div>
  );
}
