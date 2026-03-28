'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';

// Define the shape of our Job data
type Job = {
  id: string;
  title: string;
  description: string;
  requirements: string;
};

export default function JobBoard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/jobs');
        if (res.ok) {
          const data = await res.json();
          setJobs(data.jobs);
        }
      } catch (error) {
        console.error("Failed to fetch jobs:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchJobs();
  }, []);

  return (
    <main className="min-h-screen bg-gray-50 p-10 text-black">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-2">Open Positions</h1>
        <p className="text-gray-600 mb-8">Join our team and help build the future of AI tools.</p>

        {isLoading ? (
          <div className="text-center p-10 text-gray-500">Loading open roles...</div>
        ) : jobs.length === 0 ? (
          <div className="text-center p-10 bg-white rounded-lg shadow border border-gray-200">
            No open positions right now. Check back later!
          </div>
        ) : (
          <div className="grid gap-6">
            {jobs.map((job) => (
              <div key={job.id} className="bg-white p-6 rounded-lg shadow-md border border-gray-200 flex flex-col md:flex-row justify-between items-start md:items-center">
                <div className="mb-4 md:mb-0">
                  <h2 className="text-2xl font-bold text-gray-900">{job.title}</h2>
                  <p className="text-gray-600 mt-1 line-clamp-2 max-w-2xl">{job.description}</p>
                </div>
                <Link 
                  href={`/apply/${job.id}`}
                  className="bg-blue-600 text-white px-6 py-3 rounded-md font-semibold hover:bg-blue-700 transition-colors shrink-0"
                >
                  Apply Now
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}