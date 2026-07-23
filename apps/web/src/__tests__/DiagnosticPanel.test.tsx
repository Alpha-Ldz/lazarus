import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { DiagnosticPanel } from '@/components/DiagnosticPanel'
import type { Detection, RepairSheet } from '@/types'

const mockDetection: Detection = {
  class_id: 0,
  class_name: 'short',
  confidence: 0.92,
  bbox: [10, 20, 50, 60],
}

const mockRepairSheet: RepairSheet = {
  component: 'PCB trace',
  defect_type: 'short',
  severity: 'high',
  steps: ['Clean the area', 'Apply solder mask', 'Verify with multimeter'],
  estimated_cost: '$5–$20',
  difficulty: 3,
}

describe('DiagnosticPanel', () => {
  it('shows placeholder when no detection is selected', () => {
    render(<DiagnosticPanel selectedDetection={null} repairSheet={null} isLoading={false} />)
    expect(screen.getByText(/click on a detection/i)).toBeInTheDocument()
  })

  it('shows defect label and confidence when a detection is selected', () => {
    render(<DiagnosticPanel selectedDetection={mockDetection} repairSheet={null} isLoading={false} />)
    expect(screen.getByText('Short')).toBeInTheDocument()
    expect(screen.getByText(/92\.0%/)).toBeInTheDocument()
  })

  it('shows loading spinner while repair sheet is being generated', () => {
    render(<DiagnosticPanel selectedDetection={mockDetection} repairSheet={null} isLoading={true} />)
    expect(screen.getByText(/generating repair sheet/i)).toBeInTheDocument()
  })

  it('renders repair sheet steps when available', () => {
    render(<DiagnosticPanel selectedDetection={mockDetection} repairSheet={mockRepairSheet} isLoading={false} />)
    expect(screen.getByText('Clean the area')).toBeInTheDocument()
    expect(screen.getByText('Apply solder mask')).toBeInTheDocument()
    expect(screen.getByText('Verify with multimeter')).toBeInTheDocument()
  })

  it('renders severity badge', () => {
    render(<DiagnosticPanel selectedDetection={mockDetection} repairSheet={mockRepairSheet} isLoading={false} />)
    expect(screen.getByText('High')).toBeInTheDocument()
  })
})
