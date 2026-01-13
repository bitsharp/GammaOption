import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

async function getYahooFinancePrice(symbol: string) {
  try {
    const response = await fetch(
      `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=1d`,
      { 
        cache: 'no-store',
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          'Accept': 'application/json'
        }
      }
    )
    
    if (!response.ok) {
      console.error(`Yahoo Finance returned status ${response.status} for ${symbol}`)
      return null
    }
    
    const contentType = response.headers.get('content-type')
    if (!contentType || !contentType.includes('application/json')) {
      console.error(`Yahoo Finance returned non-JSON content for ${symbol}`)
      return null
    }
    
    const data = await response.json()
    
    if (data.chart?.result?.[0]?.meta?.regularMarketPrice) {
      return data.chart.result[0].meta.regularMarketPrice
    }
    
    const quotes = data.chart?.result?.[0]?.indicators?.quote?.[0]
    if (quotes?.close) {
      const prices = quotes.close.filter((p: number | null) => p !== null)
      return prices[prices.length - 1]
    }
    
    return null
  } catch (error) {
    console.error(`Error fetching ${symbol}:`, error)
    return null
  }
}

function generateMockOptions(spxPrice: number) {
  const strikes = []
  for (let strike = spxPrice - 100; strike <= spxPrice + 100; strike += 5) {
    strikes.push(strike)
  }
  
  const options = []
  
  for (const strike of strikes) {
    const distance = Math.abs(strike - spxPrice)
    
    // Calls
    const callVolume = Math.max(100, Math.floor(1000 * Math.exp(-distance / 50)))
    const callOI = Math.floor(callVolume * (2 + Math.random() * 3))
    const callGamma = 0.001 * Math.exp(-distance / 30)
    
    options.push({
      strike,
      type: 'call',
      volume: callVolume,
      open_interest: callOI,
      gamma: callGamma
    })
    
    // Puts
    const putVolume = Math.max(100, Math.floor(1200 * Math.exp(-distance / 50)))
    const putOI = Math.floor(putVolume * (2 + Math.random() * 3))
    const putGamma = 0.001 * Math.exp(-distance / 30)
    
    options.push({
      strike,
      type: 'put',
      volume: putVolume,
      open_interest: putOI,
      gamma: putGamma
    })
  }
  
  return options
}

function calculateGammaLevels(options: any[], spxPrice: number) {
  // Calculate dealer gamma
  const optionsWithGamma = options.map(opt => ({
    ...opt,
    dealer_gamma: -opt.open_interest * opt.gamma * 100,
    call_gamma: opt.type === 'call' ? -opt.open_interest * opt.gamma * 100 : 0,
    put_gamma: opt.type === 'put' ? -opt.open_interest * opt.gamma * 100 : 0
  }))
  
  // Aggregate by strike
  const strikeMap = new Map()
  
  optionsWithGamma.forEach(opt => {
    if (!strikeMap.has(opt.strike)) {
      strikeMap.set(opt.strike, {
        strike: opt.strike,
        dealer_gamma: 0,
        call_gamma: 0,
        put_gamma: 0,
        volume: 0,
        open_interest: 0,
        net_gamma: 0
      })
    }
    
    const agg = strikeMap.get(opt.strike)
    agg.dealer_gamma += opt.dealer_gamma
    agg.call_gamma += opt.call_gamma
    agg.put_gamma += opt.put_gamma
    agg.volume += opt.volume
    agg.open_interest += opt.open_interest
  })
  
  const aggregated = Array.from(strikeMap.values())
  aggregated.forEach(agg => {
    agg.net_gamma = agg.call_gamma + agg.put_gamma
  })
  
  // Sort by strike
  aggregated.sort((a, b) => a.strike - b.strike)
  
  // Find key levels
  const levels: any = {}
  
  // Put Wall - should be BELOW current price
  const putStrikes = aggregated.filter(a => a.strike < spxPrice)
  if (putStrikes.length > 0) {
    const putWall = putStrikes.reduce((max, curr) => 
      Math.abs(curr.put_gamma) > Math.abs(max.put_gamma) ? curr : max
    )
    levels.put_wall = putWall.strike
    console.log(`Put Wall found at ${putWall.strike} (below SPX ${spxPrice})`)
  }
  
  // Call Wall - should be ABOVE current price
  const callStrikes = aggregated.filter(a => a.strike > spxPrice)
  if (callStrikes.length > 0) {
    const callWall = callStrikes.reduce((max, curr) => 
      Math.abs(curr.call_gamma) > Math.abs(max.call_gamma) ? curr : max
    )
    levels.call_wall = callWall.strike
    console.log(`Call Wall found at ${callWall.strike} (above SPX ${spxPrice})`)
  }
  
  // Gamma Flip
  const nearPrice = aggregated.filter(
    a => a.strike >= spxPrice * 0.99 && a.strike <= spxPrice * 1.01
  )
  if (nearPrice.length > 0) {
    const gammaFlip = nearPrice.reduce((min, curr) => 
      Math.abs(curr.net_gamma) < Math.abs(min.net_gamma) ? curr : min
    )
    levels.gamma_flip = gammaFlip.strike
    console.log(`Gamma Flip found at ${gammaFlip.strike} (near SPX ${spxPrice})`)
  }
  
  // Determine regime
  const regime = spxPrice > (levels.gamma_flip || spxPrice) ? 'short_gamma' : 'long_gamma'
  
  return { levels, regime, aggregated }
}

export async function GET() {
  try {
    const [spxPrice, esPrice] = await Promise.all([
      getYahooFinancePrice('^GSPC'),
      getYahooFinancePrice('ES=F')
    ])
    
    // Use realistic defaults if Yahoo Finance fails
    const finalSpxPrice = spxPrice || 5950
    const finalEsPrice = esPrice || finalSpxPrice + 3.5
    const spread = finalEsPrice - finalSpxPrice
    
    console.log('Prices fetched:', { spxPrice, esPrice, finalSpxPrice, finalEsPrice, spread })
    
    // Generate options and calculate levels
    const options = generateMockOptions(finalSpxPrice)
    const { levels, regime, aggregated } = calculateGammaLevels(options, finalSpxPrice)
    
    // Convert to ES
    const esLevels: any = {}
    Object.keys(levels).forEach(key => {
      esLevels[key] = levels[key] + spread
    })
    
    // Log for debugging
    console.log('SPX Price:', finalSpxPrice)
    console.log('ES Price:', finalEsPrice)
    console.log('Spread:', spread)
    console.log('SPX Levels:', levels)
    console.log('ES Levels:', esLevels)
    
    // Limit gamma profile data for performance
    const gammaProfile = aggregated.slice(0, 50)
    
    return NextResponse.json({
      success: true,
      data: {
        spx_price: finalSpxPrice,
        es_price: finalEsPrice,
        spread: spread,
        regime: regime,
        levels_spx: levels,
        levels_es: esLevels,
        gamma_profile: gammaProfile,
        timestamp: new Date().toISOString()
      }
    })
  } catch (error: any) {
    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Failed to calculate gamma levels'
      },
      { status: 500 }
    )
  }
}
