import Navbar from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import HeatMap from "@uiw/react-heat-map";
import { CheckCircle, Circle, XCircle } from "lucide-react";
import { useEffect, useState, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useToPng } from "@hugocxl/react-to-image";

const SERVER_URL = import.meta.env.VITE_PUBLIC_SERVER_URL;

// SVG rect props for the heatmap cells
const rectProps: React.SVGProps<SVGRectElement> = { rx: 3, stroke: "#fff" };

// ---------------- Utility functions ----------------

// Sanitize input username by trimming and removing '@'
function sanitizeUsername(input: string): string {
  let username = input.trim();
  if (username.startsWith("@")) username = username.slice(1);
  return username;
}

// Validate Twitter username format
function isValidTwitterUsername(username: string): boolean {
  const sanitizedUsername = sanitizeUsername(username);
  const usernameRegex = /^(?!.*\.\.)(?!.*\.$)[A-Za-z0-9_]{1,15}$/;
  return usernameRegex.test(sanitizedUsername);
}

// Loading status messages to display while fetching/generating heatmap
const LOADING_STATUSES: string[] = [
  "Loading...",
  "Asking Elon for permission...",
  "Fetching Tweets...",
  "Generating Heatmap...",
];

// ---------------- Supabase upload ----------------
async function uploadToSupabase(username: string, dataUrl: string) {
  try {
    const formData = new FormData();
    formData.append("data_url", dataUrl);

    const response = await fetch(`${SERVER_URL}/upload/${username}`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed with status ${response.status}`);
    }

    const json = await response.json();

    if (json.error) throw new Error(json.error);

    // Return the public URL from FastAPI
    return json.url || null;
  } catch (err) {
    console.error("Upload error:", err);
    alert("Failed to upload heatmap");
    return null;
  }
}


// ---------------- Share on Twitter (X) ----------------
async function shareOnTwitter(username: string | null, dataUrl: string | null) {
  if (!username || !dataUrl) {
    alert("Unable to share on Twitter");
    return;
  }

  try {
    const publicURL = await uploadToSupabase(username, dataUrl);
    if (!publicURL) throw new Error("Failed to get public URL");

    const sharePageUrl = `${SERVER_URL}/share/${username}`;
    const text = `Check out my X heatmap! Made using @Tweet_Map_ ${sharePageUrl}`;
    const twitterIntentUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`;

    window.open(twitterIntentUrl, "_blank", "noopener,noreferrer");
  } catch (err) {
    console.error("Error sharing on Twitter:", err);
    alert("Unable to share on Twitter");
  }
}


// ---------------- Download dataURL as PNG ----------------
function downloadDataUrl(dataUrl: string | null, filename: string) {
  if (dataUrl) {
    const link = document.createElement("a");
    link.href = dataUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
  } else {
    alert("Unable to save image!");
  }
}

// ---------------- HeatmapPage Component ----------------
function HeatmapPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [isCapturing, setIsCapturing] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState(LOADING_STATUSES[0]);
  const [heatmapData, setHeatmapData] = useState<any[]>([]);
  const [userInfo, setUserInfo] = useState<any | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isRateLimited, setIsRateLimited] = useState(false);
  const [retryAfter, setRetryAfter] = useState<number | null>(null);
  const [dataURL, setDataURL] = useState<string | null>(null);

  const [savingPNG, setSavingPNG] = useState<boolean>(false);
  const [sharingToX, setSharingToX] = useState<boolean>(false);

  const navigate = useNavigate();
  const params = useParams<{ username?: string }>();
  const username = params.username ? sanitizeUsername(params.username) : "";

  const hasFetched = useRef(false); // To prevent multiple fetches
  const hasSaved = useRef(false);   // To prevent multiple captures

  // react-to-image hook for capturing heatmap as PNG
  const [{}, convert, ref] = useToPng<HTMLDivElement>({
    quality: 1.0,
    skipFonts: true,
    onSuccess: async (dataUrl) => setDataURL(dataUrl),
    onError: (error) => console.error("Error capturing image:", error),
  });

  // Automatically capture heatmap when data is ready
  useEffect(() => {
    if (!hasSaved.current && heatmapData.length > 0 && userInfo) {
      hasSaved.current = true;
      setTimeout(async () => {
        setIsCapturing(true);
        try {
          await convert();
        } catch (err) {
          console.error("Convert failed:", err);
        } finally {
          setIsCapturing(false);
        }
      }, 50);
    }
  }, [heatmapData, userInfo, convert]);

  // ---------------- Fetch tweets & generate heatmap ----------------
  useEffect(() => {
    if (!username || !isValidTwitterUsername(username)) {
      navigate("/"); // Redirect if username invalid
      return;
    }
    if (hasFetched.current) return;
    hasFetched.current = true;

    const fetchData = async () => {
      try {
        // Create job on server
        const jobRes = await fetch(`${SERVER_URL}/fetch/${username}`, { method: "POST" });
        if (!jobRes.ok && jobRes.status !== 200) {
          if (jobRes.status === 429) {
            setIsRateLimited(true);
            const retryHeader = jobRes.headers.get("Retry-After");
            if (retryHeader) setRetryAfter(parseInt(retryHeader, 10));
            throw new Error("Rate limit exceeded");
          }
          throw new Error("Failed to create job");
        }

        const { job_id, cached, result } = await jobRes.json();

        // If cached result available
        if (cached && job_id === null && result) {
          setUserInfo(result.user_info);
          const values = Object.entries(result.tweets_per_day).map(([date, count]) => ({
            date: date.replace(/-/g, "/"),
            count: count as number,
          }));
          setHeatmapData(values);
          setIsLoading(false);
          return;
        }

        // Poll job status until done
        let jobResult: any = null;
        while (job_id) {
          const res = await fetch(`${SERVER_URL}/status/${job_id}`);
          if (res.status === 429) throw new Error("Rate limit exceeded");
          if (!res.ok) throw new Error("Failed to fetch job status");

          const statusData = await res.json();
          if (statusData.status === "done") {
            const resultRes = await fetch(`${SERVER_URL}/result/${job_id}`);
            if (resultRes.status === 429) throw new Error("Rate limit exceeded");
            if (!resultRes.ok) throw new Error("Failed to fetch job result");
            jobResult = await resultRes.json();
            break;
          } else if (statusData.status === "error") {
            throw new Error(statusData.result?.error || "Job failed on server");
          }

          // Rotate loading status messages
          setLoadingStatus((prev) => {
            const idx = LOADING_STATUSES.indexOf(prev);
            return LOADING_STATUSES[(idx + 1) % LOADING_STATUSES.length];
          });

          await new Promise((resolve) => setTimeout(resolve, 5000));
        }

        if (jobResult?.user_info) {
          setUserInfo(jobResult.user_info);
          const values = Object.entries(jobResult.tweets_per_day).map(([date, count]) => ({
            date: date.replace(/-/g, "/"),
            count: count as number,
          }));
          setHeatmapData(values);
        }
        setIsLoading(false);
      } catch (error: any) {
        console.error("Fetch error:", error);
        setErrorMessage(error.message || "Something went wrong");
        setIsLoading(false);
      }
    };

    fetchData();
  }, [username, navigate]);

  // Heatmap date range: last 6 months
  const startDate = new Date();
  startDate.setMonth(startDate.getMonth() - 6);
  const endDate = new Date();

  return (
    <div className="flex flex-col overflow-hidden">
      <Navbar />

      {isRateLimited ? (
        <div className="flex justify-center items-center bg- p-4 overflow-hidden h-[calc(100vh-150px)]">
          <div>
            <div className="flex justify-center items-center">
              <XCircle className="w-12 h-12 text-yellow-500" />
            </div>
            <div className="mt-4 text-xl font-bold text-yellow-600">
              Too many requests
            </div>
            <div className="text-sm text-gray-500 mt-2">
              {retryAfter
                ? `Please try again in ${retryAfter} seconds.`
                : "Please wait a moment and try again."}
            </div>
            <div className="mt-6">
              <Button onClick={() => window.location.reload()}>Retry</Button>
            </div>
          </div>
        </div>
      ) : isLoading ? (
        <div className="flex justify-center items-center bg- p-4 overflow-hidden h-[calc(100vh-150px)]">
          <div>
            <div className="relative flex items-center justify-center">
              <Circle className="w-10 h-10 text-blue-500 animate-ping absolute opacity-75" />
              <Circle className="w-8 h-8 text-blue-500 relative" />
            </div>
            <div className="mt-10">
              <div className="text-xl font-bold">{loadingStatus}</div>
              <div className="text-sm text-gray-500 mt-4">
                This will take a few minutes
              </div>
            </div>
          </div>
        </div>
      ) : errorMessage ? (
        <div className="flex justify-center items-center bg- p-4 overflow-hidden h-[calc(100vh-150px)]">
          <div>
            <div className="flex justify-center items-center">
              <XCircle className="w-12 h-12 text-red-600" />
            </div>
            <div className="mt-6">
              <div className="text-xl font-bold text-red-600">
                Failed to fetch data
              </div>
              <div className="text-sm text-gray-500 mt-2 whitespace-pre-wrap">
                {errorMessage}
              </div>
            <div className="mt-6">
              <Button onClick={() => window.location.reload()}>Retry</Button>
            </div>
            </div>
          </div>
        </div>
      ) : (
        // Heatmap display
        <main className="flex justify-center items-center p-4 overflow-hidden h-[calc(100vh-150px)]">
          <div>
            <div ref={ref} className="p-10 pb-6 bg-white">
              {/* User info */}
              {userInfo && (
                <div className="h-20 w-2xl">
                  <div className="flex items-center justify-between">
                    <div className="flex pl-6">
                      <img src={userInfo.profile} className="w-12 h-12 rounded" />
                      <div className="ml-4 text-left">
                        <span className="font-bold flex items-center">
                          {userInfo.name}
                          {userInfo.is_verified && <CheckCircle color="#1DA1F2" size={16} className="ml-2" />}
                        </span>
                        <span className="text-sm">@{userInfo.username}</span>
                      </div>
                    </div>
                    <div className="mr-8 text-right">
                      <div className="font-semibold">{userInfo.tweet_count} Tweets</div>
                      <div className="mt-1 text-xs">
                        since {new Date(userInfo.start_date).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Heatmap */}
              <div className="h-58 px-4 py-4 w-2xl manga-border">
                <HeatMap
                  rectSize={20}
                  rectProps={rectProps}
                  style={{ height: "100%", width: "100%", fontSize: "12px" }}
                  value={heatmapData}
                  weekLabels={["", "Mon", "", "Wed", "", "Fri", ""]}
                  startDate={startDate}
                  endDate={endDate}
                  legendRender={(props) => <rect {...props} />}
                  panelColors={[ "#F0F2F5", "#CBD4DB", "#AAB8C2", "#1D9BF0", "#075fa6"]}
                />
              </div>
              <div className="text-xs mt-6 text-right text-gray-500">Made using @Tweet_Map_</div>
            </div>

            {/* Action buttons */}
            <div className="mt-8 flex justify-evenly">
              <Button
                onClick={() => {
                  setSavingPNG(true); 
                  downloadDataUrl(dataURL, "heatmap.png"); 
                  setSavingPNG(false);
                }}
                disabled={isCapturing}
                className="hover:cursor-pointer"
              >
                {savingPNG ? (
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 animate-spin text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
                    </svg>
                    Rendering...
                  </div>
                ) : "Save as PNG"}
              </Button>

              <Button
                onClick={async () => {
                  setSharingToX(true);
                  await shareOnTwitter(username, dataURL);
                  setSharingToX(false);
                }}
                disabled={isCapturing}
                className="hover:cursor-pointer"
              >
                {sharingToX ? (
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 animate-spin text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
                    </svg>
                    Sharing...
                  </div>
                ) : "Share on X"}
              </Button>
            </div>
          </div>
        </main>
      )}
    </div>
  );
}

export default HeatmapPage;


