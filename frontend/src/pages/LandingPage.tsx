import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ArrowRight } from "lucide-react"
import '../App.css'

function LandingPage() {
  return (
    <div className="flex flex-col overflow-hidden">
      {/* Topbar */}
      <header className="w-full h-14 flex-shrink-0">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between">
          <div className='flex justify-center items-center'>
            <span className='text-xl mr-4 text-white bg-black p-2 rounded w-10 flex items-center justify-center'>
              𝕏
            </span>
            <span className="text-2xl font-bold tracking-tight">
              Tweet Map
            </span>
          </div>
          <div>
            <span className="ml-4 mr-4">
              Github
            </span>
            <span className="ml-4 mr-4">
              Twitter
            </span>
          </div>
        </div>
      </header>

      {/* Full height minus header */}
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
              <Input type="email" placeholder="X/Twitter username" className="block w-full h-10 manga-border px-3 py-2 text-xl bg-white focus:outline-none focus:ring-2 focus:ring-black rounded"/>
              <Button type="submit" variant="outline" className="manga-border manga-text py-2 px-3 text-sm h-10 font-black ml-1 text-black hover:text-white hover:bg-black focus:outline-none disabled:opacity-50 transform cursor-pointer">
                <ArrowRight/>
              </Button>
            </div>
          </div>
          <div className="text-xs text-gray-600 mt-4">
            No signup required! 
          </div>  
        </div>
      </main>
      <footer>
        <div className="">
          Made with 💙 by @sakkshm
        </div>
      </footer>
    </div>
  )
}

export default LandingPage
