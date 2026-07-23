import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useAnalyze } from '@/hooks/useAnalyze'

describe('useAnalyze', () => {
  beforeEach(() => {
    // Mock URL.createObjectURL used when loading the image
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:mock')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('starts with empty state', () => {
    const { result } = renderHook(() => useAnalyze())
    expect(result.current.detections).toEqual([])
    expect(result.current.isAnalyzing).toBe(false)
    expect(result.current.error).toBeNull()
    expect(result.current.repairSheet).toBeNull()
  })

  it('reset clears all state', async () => {
    const { result } = renderHook(() => useAnalyze())
    act(() => result.current.reset())
    expect(result.current.detections).toEqual([])
    expect(result.current.error).toBeNull()
    expect(result.current.repairSheet).toBeNull()
  })

  it('sets error when API returns non-ok response', async () => {
    // Stub Image constructor so it fires onload immediately
    class MockImage {
      naturalWidth = 640
      naturalHeight = 480
      onload: (() => void) | null = null
      set src(_: string) { setTimeout(() => this.onload?.(), 0) }
    }
    vi.stubGlobal('Image', MockImage)

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      statusText: 'Service Unavailable',
    }))

    const { result } = renderHook(() => useAnalyze())
    const file = new File(['img'], 'test.jpg', { type: 'image/jpeg' })

    await act(async () => {
      await result.current.analyze(file)
    })

    expect(result.current.error).toMatch(/Service Unavailable/)
    expect(result.current.detections).toEqual([])
    expect(result.current.isAnalyzing).toBe(false)
  })
})
