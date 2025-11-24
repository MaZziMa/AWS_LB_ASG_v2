import React, { useState, useEffect } from 'react';
import { enrollmentsAPI, coursesAPI, studentsAPI } from '../services/api';

export default function EnrollmentList() {
  const [enrollments, setEnrollments] = useState([]);
  const [courses, setCourses] = useState([]);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    enrollment_id: '',
    student_id: '',
    course_id: '',
    enrolled_date: new Date().toISOString().split('T')[0],
    progress: 0,
    completed: false
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [enrollmentRes, courseRes, studentRes] = await Promise.all([
        enrollmentsAPI.getAll(),
        coursesAPI.getAll(),
        studentsAPI.getAll()
      ]);
      setEnrollments(enrollmentRes.data.enrollments || []);
      setCourses(courseRes.data.courses || []);
      setStudents(studentRes.data.students || []);
      setError(null);
    } catch (err) {
      setError('Failed to load data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await enrollmentsAPI.create({
        ...formData,
        progress: parseInt(formData.progress)
      });
      setShowForm(false);
      setFormData({
        enrollment_id: '',
        student_id: '',
        course_id: '',
        enrolled_date: new Date().toISOString().split('T')[0],
        progress: 0,
        completed: false
      });
      fetchData();
    } catch (err) {
      alert('Failed to create enrollment: ' + err.message);
    }
  };

  const getStudentName = (studentId) => {
    const student = students.find(s => s.student_id === studentId);
    return student ? student.name : studentId;
  };

  const getCourseTitle = (courseId) => {
    const course = courses.find(c => c.course_id === courseId);
    return course ? course.title : courseId;
  };

  if (loading) {
    return <div className="text-center py-8">Loading enrollments...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Enrollments</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-primary text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition"
        >
          {showForm ? 'Cancel' : '+ Add Enrollment'}
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input
              type="text"
              placeholder="Enrollment ID (e.g., ENR001)"
              value={formData.enrollment_id}
              onChange={(e) => setFormData({ ...formData, enrollment_id: e.target.value })}
              className="border px-3 py-2 rounded"
              required
            />
            <select
              value={formData.student_id}
              onChange={(e) => setFormData({ ...formData, student_id: e.target.value })}
              className="border px-3 py-2 rounded"
              required
            >
              <option value="">Select Student</option>
              {students.map(s => (
                <option key={s.student_id} value={s.student_id}>
                  {s.name} ({s.student_id})
                </option>
              ))}
            </select>
            <select
              value={formData.course_id}
              onChange={(e) => setFormData({ ...formData, course_id: e.target.value })}
              className="border px-3 py-2 rounded"
              required
            >
              <option value="">Select Course</option>
              {courses.map(c => (
                <option key={c.course_id} value={c.course_id}>
                  {c.title} ({c.course_id})
                </option>
              ))}
            </select>
            <input
              type="date"
              value={formData.enrolled_date}
              onChange={(e) => setFormData({ ...formData, enrolled_date: e.target.value })}
              className="border px-3 py-2 rounded"
              required
            />
            <input
              type="number"
              min="0"
              max="100"
              placeholder="Progress (%)"
              value={formData.progress}
              onChange={(e) => setFormData({ ...formData, progress: e.target.value })}
              className="border px-3 py-2 rounded"
            />
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={formData.completed}
                onChange={(e) => setFormData({ ...formData, completed: e.target.checked })}
                className="w-4 h-4"
              />
              <span>Completed</span>
            </label>
          </div>
          <button
            type="submit"
            className="mt-4 bg-secondary text-white px-6 py-2 rounded hover:bg-green-600 transition"
          >
            Create Enrollment
          </button>
        </form>
      )}

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Student</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Course</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Progress</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {enrollments.map((enrollment) => (
              <tr key={enrollment.enrollment_id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {enrollment.enrollment_id}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {getStudentName(enrollment.student_id)}
                </td>
                <td className="px-6 py-4 text-sm text-gray-900">
                  {getCourseTitle(enrollment.course_id)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(enrollment.enrolled_date).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  <div className="flex items-center">
                    <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                      <div
                        className="bg-primary h-2 rounded-full"
                        style={{ width: `${enrollment.progress}%` }}
                      ></div>
                    </div>
                    <span>{enrollment.progress}%</span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                    enrollment.completed
                      ? 'bg-green-100 text-green-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {enrollment.completed ? 'Completed' : 'In Progress'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {enrollments.length === 0 && !loading && (
          <div className="text-center py-12 text-gray-500">
            No enrollments found. Create your first enrollment to get started!
          </div>
        )}
      </div>
    </div>
  );
}
