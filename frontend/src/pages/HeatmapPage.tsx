import HeatMap from '@uiw/react-heat-map';

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
  x: 5,
  y: 5,
  width: 120,
  height: 80,
  rx: 2,
  stroke: '#fff',
  onClick: () => alert("Rectangle clicked!")
};

function HeatmapPage() {
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
        <div className='h-full w-full'>
            <HeatMap
                rectSize={15}
                rectProps={rectProps}
                className='h-full w-full'
                value={value}
                weekLabels={['', 'Mon', '', 'Wed', '', 'Fri', '']}
                startDate={new Date('2025/01/01')}
                endDate={new Date()}
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
      </main>
      <footer>
        <div className="">
          Made with 💙 by @sakkshm
        </div>
      </footer>
    </div>
  )
}

export default HeatmapPage