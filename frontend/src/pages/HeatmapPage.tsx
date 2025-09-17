import Footer from '@/components/Footer';
import Navbar from '@/components/Navbar';
import HeatMap from '@uiw/react-heat-map';
import { CheckCircle, Circle} from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

const value = [
  { date: '2016/01/11', count: 2 },
  { date: '2016/01/12', count: 20 },
  { date: '2016/01/13', count: 10 },
  ...[...Array(20)].map((_, idx) => ({
    date: `2025/08/${idx + 10}`, count: idx, content: ''
  })),
  { date: '2016/04/11', count: 2 },
  { date: '2016/05/01', count: 5 },
  { date: '2016/05/02', count: 5 },
  { date: '2016/05/04', count: 11 },
];

const rectProps: React.SVGProps<SVGRectElement> = {
  rx: 3,
  stroke: '#fff'
};

function sanitizeUsername(input: string): string {
  let username = input.trim();
  
  if (username.startsWith("@")) {
    username = username.slice(1);
  }

  return username;
}

function isValidTwitterUsername(username: string): boolean {
  const sanitizedUsername = sanitizeUsername(username);
  const usernameRegex = /^(?!.*\.\.)(?!.*\.$)[A-Za-z0-9_]{1,15}$/;
  return usernameRegex.test(sanitizedUsername);
}

const LOADING_STATUSES: string[] = [
  "Loading...",
  "Asking Elon for permission...",
  "Fetching Tweets...",
  "Generating Heatmap..."
]

function HeatmapPage() {

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [loadingStatus, setLoadingStatus] = useState<string>(LOADING_STATUSES[0]);
  const navigate = useNavigate();
  const params = useParams<{ username?: string }>();
  const username = params.username;
  
  useEffect(() => {
    if(!params || !username || !isValidTwitterUsername(username)){
      navigate("/");
    }
  }, [username, navigate])

  const startDate = new Date();
  startDate.setMonth(startDate.getMonth() - 6);
  
  const endDate = new Date();

  return (
    <div className="flex flex-col overflow-hidden">
      <Navbar/>
      {
        isLoading ?
        <main className="flex justify-center items-center p-4 overflow-hidden h-[calc(100vh-150px)]">
          <div>
            <div className='pl-4 h-20 w-2xl '>
              <div className='flex items-center justify-between'>
                <div className='flex'>
                  <div>
                    <img src="/default_profile.png" className='w-12 h-12 rounded'/>
                  </div>
                  <div className='ml-4 text-left'>
                    <span className='font-bold flex items-center '>
                      Saksham Saxena 
                    <CheckCircle color="#1DA1F2" size={16} className='ml-2' />
                    </span>
                    <span className='text-sm'>
                      {`@${username}`}
                    </span>
                  </div>
                </div>
                <div className='mr-8'>
                  <div className='mr-2 font-semibold'>
                    20 Tweets
                  </div>
                  <span className='text-xs'>
                    since 26 Jul 2016
                  </span>
                </div>
              </div>
            </div>
          
            <div className='h-58 px-4 py-4 w-2xl manga-border'>
                <HeatMap
                    rectSize={20}
                    rectProps={rectProps}
                    style={{ height: '100%', width: '100%' , fontSize: '12px'}}
                    value={value}
                    weekLabels={['', 'Mon', '', 'Wed', '', 'Fri', '']}
                    startDate={startDate}
                    endDate={endDate}
                    legendRender={(props) => <rect {...props} />}
                    panelColors={
                        [
                        "#EFF3F4", // very light gray (no activity)
                        "#CFD9DE", // soft gray
                        "#AAB8C2", // muted gray-blue
                        "#1D9BF0", // X blue (medium activity)
                        "#0C7ABF"  // dark blue (high activity)
                        ]
                    }
                />
            </div>
          </div>
        </main>
        :
        <nav className="flex flex-col overflow-hidden">
          <div className="w-full h-[calc(100vh-150px)] flex items-center justify-center">
          <div>
            <div className="relative flex items-center justify-center">
              <Circle className="w-10 h-10 text-blue-500 animate-ping absolute opacity-75" />
              <Circle className="w-8 h-8 text-blue-500 relative" />
            </div>

            <div className='flex justify-center items-center mt-10'>
              <div>
                <div className='text-xl font-bold'>
                  {loadingStatus}
                </div>
                <div className='text-sm text-gray-500 mt-4'>
                  This will take a few minutes
                </div>
              </div>
            </div>
          </div>

          </div>
        </nav>
      }
      <Footer/>
    </div>
  )
}

export default HeatmapPage