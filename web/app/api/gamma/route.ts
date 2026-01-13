import { NextResponse } from 'next/server'
import { promises as fs } from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    // Prefer Python-generated cache when running locally
    // (GammaOption/data/latest_levels.json created by `python main.py analyze`)
    const cachePath = path.resolve(process.cwd(), '..', 'data', 'latest_levels.json')
    try {
      const raw = await fs.readFile(cachePath, 'utf-8')
      const cached = JSON.parse(raw)

      const converted = cached?.converted_levels || {}
      const levels_spx: any = {}
      const levels_es: any = {}
      Object.keys(converted).forEach((k) => {
        if (converted[k]?.spx != null) levels_spx[k] = converted[k].spx
        if (converted[k]?.es != null) levels_es[k] = converted[k].es
      })

      return NextResponse.json({
        success: true,
        data: {
          spx_price: cached?.spx_price,
          es_price: cached?.es_price,
          spread: cached?.spread,
          regime: cached?.regime,
          levels_spx,
          levels_es,
          gamma_profile: cached?.gamma_profile || [],
          timestamp: cached?.timestamp || new Date().toISOString(),
          source: 'python-cache'
        }
      })
    } catch {
      // Cache not present/parseable: return No data
    }
    return NextResponse.json(
      {
        success: false,
        error: 'No data available. Run the Python analysis to generate levels.'
      },
      { status: 503 }
    )
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
