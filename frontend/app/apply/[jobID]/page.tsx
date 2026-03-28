'use client';
import { useState } from 'react';
import { useRouter, useParams } from 'next/navigation'; // <-- 1. Import useParams

export default function ApplyPage() {
  const [file, setFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const router = useRouter();
  const params = useParams(); // <-- 2. Initialize useParams

const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);

    const formData = new FormData(e.currentTarget);
    if (file) formData.append('file', file);
    
    // 3. THE NUCLEAR OPTION: Read the URL directly from the browser
    const pathSegments = window.location.pathname.split('/');
    const currentJobId = pathSegments[pathSegments.length - 1]; 

    // Safety Net: Stop it before it crashes the backend if the ID is wrong
    if (!currentJobId || currentJobId === 'undefined' || currentJobId === '[jobId]') {
        alert("Wait! The Job ID is missing from the URL. Please go back to the Home page and click 'Apply Now' on a specific job.");
        setIsSubmitting(false);
        return;
    }

    formData.append('job_id', currentJobId); 

    try {
      const res = await fetch('http://127.0.0.1:8000/api/apply', {
        method: 'POST',
        body: formData,
      });
      
      if (res.ok) {
        router.push('/success');
      } else {
        const errorData = await res.json();
        alert(`Backend Error: ${errorData.detail || 'Something went wrong.'}`);
        setIsSubmitting(false);
      }
    } catch (error) {
      console.error("Fetch error:", error);
      alert("Network error. Make sure the backend is running!");
      setIsSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center p-24 bg-gray-50 text-black">
      <h1 className="text-4xl font-bold mb-8 text-black">Submit Application</h1>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 w-full max-w-md bg-white p-8 rounded-lg shadow-xl text-black border border-gray-200">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
          <input name="name" placeholder="Jane Doe" required className="border border-gray-300 p-2 rounded w-full" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input name="email" type="email" placeholder="jane@example.com" required className="border border-gray-300 p-2 rounded w-full" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Resume (PDF)</label>
          <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} required className="border border-gray-300 p-2 rounded w-full" />
        </div>
        <button 
          type="submit" 
          disabled={isSubmitting}
          className={`mt-4 p-3 rounded text-white font-semibold transition-colors ${
            isSubmitting ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {isSubmitting ? 'Submitting & AI Screening...' : 'Submit Application'}
        </button>
      </form>
    </main>
  );
}