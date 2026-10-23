import { setupHttpClient } from './api/http';
import { bootstrapDashboard } from './bootstrapDashboard';
import '@/scss/style.scss';
import '@/assets/fonts/fonts.css';

setupHttpClient();

void bootstrapDashboard().catch((error: unknown) => {
  console.error('Dashboard failed to mount:', error);
});
