import { useState, useEffect, useRef } from 'react'

const SEAT_IDS = [1, 2, 3, 4, 5, 6, 7, 8]

function App() {
  const [seats, setSeats] = useState(
    Object.fromEntries(SEAT_IDS.map(id => [id, 'available']))
  )
  const wsRef = useRef(null)

  useEffect(() => {
    function connect() {
      const ws = new WebSocket('ws://localhost:8000/ws')
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
      }

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        console.log('Received:', data)
        setSeats(prev => ({ ...prev, [data.seat_id]: data.status }))
      }

      ws.onclose = () => {
        console.log('WebSocket closed, reconnecting in 1s...')
        setTimeout(connect, 1000)
      }

      ws.onerror = (err) => {
        console.log('WebSocket error:', err)
      }
    }

    connect()

    return () => {
      if (wsRef.current) wsRef.current.onclose = null
      if (wsRef.current) wsRef.current.close()
    }
  }, [])

  const holdSeat = async (seatId) => {
    const res = await fetch(`http://localhost:8000/seats/${seatId}/hold?user_id=user_1`, {
      method: 'POST'
    })
    const data = await res.json()
    if (!data.held) {
      alert('Seat already taken!')
    }
  }

  return (
    <div style={{ padding: '2rem' }}>
      <h1>SeatLive</h1>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        {SEAT_IDS.map(id => (
          <button
            key={id}
            onClick={() => holdSeat(id)}
            style={{
              width: '80px',
              height: '80px',
              backgroundColor: seats[id] === 'available' ? 'green' : 'red',
              color: 'white',
              fontSize: '1rem',
              cursor: seats[id] === 'available' ? 'pointer' : 'not-allowed',
              border: 'none',
              borderRadius: '8px'
            }}
          >
            Seat {id}
          </button>
        ))}
      </div>
    </div>
  )
}

export default App
