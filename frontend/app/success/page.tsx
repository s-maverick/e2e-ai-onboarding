// frontend/src/app/success/page.tsx
import Link from 'next/link';

export default function SuccessPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24 bg-gray-50 text-black">
      <div className="bg-white p-10 rounded-lg shadow-xl text-center max-w-lg border border-gray-200">
        
        <div className="text-green-500 text-6xl mb-4">✓</div>
        <h1 className="text-3xl font-bold text-gray-900 mb-4">Application Received!</h1>
        
        <p className="text-lg text-gray-700 mb-6">
          Thank you for applying. Our AI agent is currently reviewing your resume and matching your skills against the job description.
        </p>
        
        <p className="text-sm text-gray-500 mb-8 p-4 bg-gray-100 rounded">
          <strong>Next Steps:</strong> If your profile is a strong match, you will receive an automated email within the next 5 minutes with a link to schedule your interview.
        </p>
        
        <Link 
          href="/" 
          className="bg-blue-600 text-white px-6 py-3 rounded font-semibold hover:bg-blue-700 transition-colors inline-block"
        >
          Return to Job Board
        </Link>
        
      </div>
    </main>
  );
}