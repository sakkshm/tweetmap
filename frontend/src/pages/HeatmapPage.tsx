import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import HeatMap from "@uiw/react-heat-map";
import { CheckCircle, Circle } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useToPng } from "@hugocxl/react-to-image";

// const value = [
//   { date: "2025/06/11", count: 2 },
//   { date: "2025/06/12", count: 20 },
//   { date: "2025/07/13", count: 10 },
//   ...[...Array(20)].map((_, idx) => ({
//     date: `2025/09/${idx - 2}`,
//     count: idx,
//     content: "",
//   })),
//   { date: "2025/08/11", count: 2 },
//   { date: "2025/08/01", count: 5 },
//   { date: "2025/08/02", count: 5 },
//   { date: "2025/08/04", count: 11 },
// ];

const value = Array.from({ length: 190 }, (_, i) => {
  const d = new Date();
  d.setDate(d.getDate() - (190 - i));
  return {
    date: `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`,
    count: Math.floor(Math.random() * 10) + 1, // random 1-5
  };
});



const rectProps: React.SVGProps<SVGRectElement> = {
  rx: 3,
  stroke: "#fff",
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
  "Generating Heatmap...",
];

function HeatmapPage() {
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [loadingStatus, setLoadingStatus] = useState<string>(
    LOADING_STATUSES[0]
  );
  const navigate = useNavigate();
  const params = useParams<{ username?: string }>();
  const username = params.username;

  // react-to-image hook
  const [{ isLoading: isCapturing }, convert, ref] = useToPng<HTMLDivElement>({
    quality: 1.0,
    skipFonts: true,
    onSuccess: (dataUrl) => {
      const link = document.createElement("a");
      link.download = "heatmap.png";
      link.href = dataUrl;
      link.click();
    },
    onError: (error) => {
      console.error("Error capturing image:", error);
    },
  });

  useEffect(() => {
    if (!params || !username || !isValidTwitterUsername(username)) {
      navigate("/");
    }

    // fake load
    const timer = setTimeout(() => setIsLoading(true), 500);
    return () => clearTimeout(timer);
  }, [username, navigate]);

  const startDate = new Date();
  startDate.setMonth(startDate.getMonth() - 6);
  const endDate = new Date();

  return (
    <div className="flex flex-col overflow-hidden">
      <Navbar />
      {isLoading ? (
        <main className="flex justify-center items-center p-4 overflow-hidden h-[calc(100vh-150px)]">
          <div>
            {/* Only wrap header + heatmap inside ref */}
            <div ref={ref} className="p-10 pb-6">
              {/* Header */}
              <div className="h-20 w-2xl">
                <div className="flex items-center justify-between">
                  <div className="flex pl-6">
                    <div>
                      <img
                        src="/default_profile.png"
                        className="w-12 h-12 rounded"
                      />
                    </div>
                    <div className="ml-4 text-left">
                      <span className="font-bold flex items-center">
                        Saksham Saxena
                        <CheckCircle
                          color="#1DA1F2"
                          size={16}
                          className="ml-2"
                        />
                      </span>
                      <span className="text-sm">{`@${username}`}</span>
                    </div>
                  </div>
                  <div className="mr-8">
                    <div className="mr-2 font-semibold text-right">
                      20 Tweets
                    </div>
                    <span className="text-xs">since 26 Jul 2025</span>
                  </div>
                </div>
              </div>

              {/* Heatmap */}
              <div className="h-58 px-4 py-4 w-2xl manga-border">
                <HeatMap
                  rectSize={20}
                  rectProps={rectProps}
                  style={{ height: "100%", width: "100%", fontSize: "12px" }}
                  value={value}
                  weekLabels={["", "Mon", "", "Wed", "", "Fri", ""]}
                  startDate={startDate}
                  endDate={endDate}
                  legendRender={(props) => <rect {...props} />}
                  panelColors={[
                    "#F0F2F5",  
                    "#CBD4DB",  
                    "#AAB8C2",  
                    "#1D9BF0",  
                    "#075fa6", 
                  ]}
                />
              </div>
              <div className="text-xs mt-6 text-right text-gray-500">
                Made using @Tweet_Map_
              </div>
            </div>

            {/* Buttons outside of ref */}
            <div className="mt-4 flex justify-evenly">
              <Button onClick={convert} disabled={isCapturing}>
                {isCapturing ? "Rendering..." : "Save as PNG"}
              </Button>
              <Button>Share on X</Button>
            </div>
          </div>
        </main>
      ) : (
        <nav className="flex flex-col overflow-hidden">
          <div className="w-full h-[calc(100vh-150px)] flex items-center justify-center">
            <div>
              <div className="relative flex items-center justify-center">
                <Circle className="w-10 h-10 text-blue-500 animate-ping absolute opacity-75" />
                <Circle className="w-8 h-8 text-blue-500 relative" />
              </div>

              <div className="flex justify-center items-center mt-10">
                <div>
                  <div className="text-xl font-bold">{loadingStatus}</div>
                  <div className="text-sm text-gray-500 mt-4">
                    This will take a few minutes
                  </div>
                </div>
              </div>
            </div>
          </div>
        </nav>
      )}
      <Footer />
    </div>
  );
}

export default HeatmapPage;
