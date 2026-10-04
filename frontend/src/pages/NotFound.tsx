import { useNavigate } from 'react-router-dom';
import { Compass } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/States';

export default function NotFound() {
  const navigate = useNavigate();
  return (
    <div className="p-4 sm:p-8 max-w-3xl mx-auto">
      <EmptyState
        icon={Compass}
        title="Page not found"
        description="The page you're looking for doesn't exist or has moved."
        action={<Button onClick={() => navigate('/dashboard')}>Back to dashboard</Button>}
      />
    </div>
  );
}
