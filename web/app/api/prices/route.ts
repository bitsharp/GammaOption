import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

async function getYahooFinancePrice(symbol: string) {
  try {
    const response = await fetch(
      `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1m&range=1d`,
      { cache: 'no-store' }
    )
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

export async function GET() {
  try {
    const [spxPrice, esPrice] = await Promise.all([
      getYahooFinancePrice('^GSPC'),
      getYahooFinancePrice('ES=F')
    ])
    
    const spread = spxPrice && esPrice ? esPrice - spxPrice : null
    
    return NextResponse.json({
      success: true,
      data: {
        spx: spxPrice,
        es: esPrice,
        spread: spread,
        timestamp: new Date().toISOString()
      }
    })
  } catch (error: any) {
    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Failed to fetch prices'
      },
      { status: 500 }
    )
  }
}
