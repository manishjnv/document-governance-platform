/**
 * T-2009: Generic analytics chart wrapper component
 * Decoupled from any specific data source; accepts labels and datasets
 * Uses react-chartjs-2 for rendering (Chart.js)
 *
 * ponytail: the analytics API is a later wave, not built yet — wire a data source
 * in when it lands. This component is purely presentational.
 */

'use client';

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend);

interface Dataset {
  label: string;
  data: number[];
  borderColor?: string;
  backgroundColor?: string;
  borderWidth?: number;
  tension?: number; // For line charts
  fill?: boolean;
}

interface AnalyticsChartProps {
  title?: string;
  labels: string[];
  datasets: Dataset[];
  type?: 'line' | 'bar';
  height?: number;
}

const DEFAULT_COLORS = [
  '#9333EA', // purple
  '#3B82F6', // blue
  '#10B981', // green
  '#F59E0B', // amber
  '#EF4444', // red
  '#8B5CF6', // violet
];

export default function AnalyticsChart({
  title,
  labels,
  datasets,
  type = 'line',
  height = 300,
}: AnalyticsChartProps) {
  // Auto-assign colors if not provided
  const enrichedDatasets = datasets.map((ds, idx) => ({
    ...ds,
    borderColor: ds.borderColor || DEFAULT_COLORS[idx % DEFAULT_COLORS.length],
    backgroundColor:
      ds.backgroundColor || DEFAULT_COLORS[idx % DEFAULT_COLORS.length].replace(')', ', 0.1)'),
    borderWidth: ds.borderWidth ?? 2,
    tension: ds.tension ?? 0.4,
    fill: ds.fill ?? (type === 'line' ? false : true),
  }));

  const chartData = {
    labels,
    datasets: enrichedDatasets,
  };

  const chartOptions: ChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          usePointStyle: true,
          padding: 15,
          font: { size: 12, weight: '500' },
        },
      },
      title: title
        ? {
            display: true,
            text: title,
            font: { size: 14, weight: 'bold' },
            padding: { bottom: 20 },
          }
        : undefined,
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleFont: { size: 12, weight: 'bold' },
        bodyFont: { size: 12 },
        padding: 10,
        displayColors: true,
        borderColor: '#ddd',
        borderWidth: 1,
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(0, 0, 0, 0.05)' },
        ticks: { font: { size: 11 } },
      },
      y: {
        grid: { color: 'rgba(0, 0, 0, 0.05)' },
        ticks: { font: { size: 11 } },
        beginAtZero: true,
      },
    },
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div style={{ height }} role="img" aria-label={title || 'Chart'}>
        {type === 'line' ? (
          <Line data={chartData} options={chartOptions} />
        ) : (
          <Bar data={chartData} options={chartOptions} />
        )}
      </div>
    </div>
  );
}
