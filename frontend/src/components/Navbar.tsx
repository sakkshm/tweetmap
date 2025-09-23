import { Link } from "react-router-dom"

function Navbar() {
  return (
    <header className="w-full h-14 flex-shrink-0">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between">
          <Link to="/">
            <div className='flex justify-center items-center'>
                <span className='text-xl mr-4 text-white bg-black p-1 rounded w-10 flex items-center justify-center'>
                <img src="/logo.png"/>
                </span>
                <span className="text-2xl font-bold tracking-tight">
                Tweet Map
                </span>
            </div>
          </Link>
          <div>
            <a href="https://github.com/sakkshm/tweetmap">
                <span className="ml-4 mr-4 hover:underline">
                Github
                </span>
            </a>
            <a href="https://x.com/Tweet_Map_">
                <span className="ml-4 mr-4 hover:underline">
                Twitter
                </span>
            </a>
          </div>
        </div>
    </header>
  )
}

export default Navbar