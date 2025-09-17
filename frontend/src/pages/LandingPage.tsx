import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ArrowRight } from "lucide-react"
import '../App.css'
import { useState } from "react"
import { useNavigate, type NavigateFunction } from "react-router-dom"
import Footer from "@/components/Footer"
import Navbar from "@/components/Navbar"

function navigateToHeatmapPage(navigate: NavigateFunction, username: string){
  const sanitizedUsername = sanitizeUsername(username);
  navigate(`/heatmap/${sanitizedUsername}`);
}

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
 
function LandingPage() {

  const [username, setUsername] = useState<string>("");
  const [usernameError, setUsernameError] = useState<boolean>(false);
  const navigate = useNavigate();

  return (
    <div className="flex flex-col overflow-hidden">
      <Navbar/>
      <main className="flex justify-center items-center p-4 overflow-hidden h-[calc(100vh-150px)]">
        <div className="text-center">
          <h1 className='text-4xl font-extrabold'>
            Visualise your activity on 𝕏.
          </h1>
          <h3 className='text-xl text-gray-500 mt-6'>
            Visualize when you tweet the most with a clean, <br/>GitHub-like heatmap.
          </h3>

          <div className='flex justify-center mt-12'>
            <div className="flex w-full max-w-sm items-center gap-2">
              
              <Input type="email" placeholder="X/Twitter username" className="block w-full h-10 manga-border px-3 py-2 text-xl bg-white focus:outline-none focus:ring-2 focus:ring-black rounded" onChange={(e) => {
                setUsernameError(false);
                setUsername(e.target.value)
              }}/>

              <Button type="submit" variant="outline" className="manga-border manga-text py-2 px-3 text-sm h-10 font-black ml-1 text-black hover:text-white hover:bg-black focus:outline-none disabled:opacity-50 transform cursor-pointer" onClick={() => {
                if(isValidTwitterUsername(username)){
                  navigateToHeatmapPage(navigate, username);
                }
                else{
                  setUsernameError(true);
                }
              }}>
                <ArrowRight/>
              </Button>
            
            </div>
          </div>
            {
              usernameError ? 
                <div className="text-xs text-red-800 mt-4">
                  Invalid username! 
                </div>   
                :
                <div className="text-xs text-gray-600 mt-4">
                  No signup required! 
                </div> 
            }
        </div>
      </main>
      <Footer/>
    </div>
  )
}

export default LandingPage
