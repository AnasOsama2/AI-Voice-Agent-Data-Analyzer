import React from 'react';
import { ChartConfig } from '../types';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';
import { BarChart3, TrendingUp, PieChart as PieIcon, Activity } from 'lucide-react';

interface ChartRendererProps {
  data: Record<string, any>[];
  config: ChartConfig;
  columns: string[];
}

const PALETTE = [
  '#6366f1', // Indigo
  '#a855f7', // Purple
  '#38bdf8', // Sky
  '#10b981', // Emerald
  '#f59e0b', // Amber
  '#f43f5e', // Rose
  '#8b5cf6', // Violet
  '#06b6d4', // Cyan
];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="custom-chart-tooltip">
        <p className="tooltip-label">{`${label || ''}`}</p>
        {payload.map((entry: any, index: number) => (
          <p key={`item-${index}`} className="tooltip-item" style={{ color: entry.color }}>
            <span className="tooltip-name">{entry.name}: </span>
            <span className="tooltip-value font-mono">
              {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
            </span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export const ChartRenderer: React.FC<ChartRendererProps> = ({ data, config, columns }) => {
  if (!data || data.length === 0) return null;

  const chartType = config.chart_type || 'bar';
  const xKey = config.x_key || columns[0] || 'category';
  const yKeys =
    config.y_keys && config.y_keys.length > 0
      ? config.y_keys
      : columns.filter((c) => c !== xKey).slice(0, 3);

  // Format data for numeric casting
  const formattedData = data.map((d) => {
    const formattedItem: Record<string, any> = { ...d };
    yKeys.forEach((k) => {
      const val = Number(d[k]);
      formattedItem[k] = isNaN(val) ? 0 : val;
    });
    return formattedItem;
  });

  const getChartIcon = () => {
    switch (chartType) {
      case 'bar':
        return <BarChart3 size={16} color="#6366f1" />;
      case 'line':
        return <TrendingUp size={16} color="#38bdf8" />;
      case 'area':
        return <Activity size={16} color="#10b981" />;
      case 'pie':
        return <PieIcon size={16} color="#a855f7" />;
      default:
        return <BarChart3 size={16} color="#6366f1" />;
    }
  };

  return (
    <div className="chart-card">
      <div className="chart-card-header">
        <div className="flex items-center gap-2">
          {getChartIcon()}
          <h4 className="chart-title">{config.title || `${chartType.toUpperCase()} Chart Analytics`}</h4>
        </div>
        <span className="chart-badge">{chartType.toUpperCase()}</span>
      </div>

      <div className="chart-canvas-container" style={{ width: '100%', height: 320 }}>
        <ResponsiveContainer width="100%" height="100%">
          {(() => {
            switch (chartType) {
              case 'line':
                return (
                  <LineChart data={formattedData} margin={{ top: 15, right: 25, left: 0, bottom: 25 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis
                      dataKey={xKey}
                      stroke="#94a3b8"
                      fontSize={12}
                      tickLine={false}
                      angle={-20}
                      textAnchor="end"
                    />
                    <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ paddingTop: 10 }} />
                    {yKeys.map((key, idx) => (
                      <Line
                        key={key}
                        type="monotone"
                        dataKey={key}
                        name={key}
                        stroke={PALETTE[idx % PALETTE.length]}
                        strokeWidth={2.5}
                        dot={{ r: 4, fill: PALETTE[idx % PALETTE.length] }}
                        activeDot={{ r: 7 }}
                      />
                    ))}
                  </LineChart>
                );

              case 'area':
                return (
                  <AreaChart data={formattedData} margin={{ top: 15, right: 25, left: 0, bottom: 25 }}>
                    <defs>
                      {yKeys.map((key, idx) => (
                        <linearGradient key={key} id={`grad-${idx}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={PALETTE[idx % PALETTE.length]} stopOpacity={0.4} />
                          <stop offset="95%" stopColor={PALETTE[idx % PALETTE.length]} stopOpacity={0.0} />
                        </linearGradient>
                      ))}
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis
                      dataKey={xKey}
                      stroke="#94a3b8"
                      fontSize={12}
                      tickLine={false}
                      angle={-20}
                      textAnchor="end"
                    />
                    <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ paddingTop: 10 }} />
                    {yKeys.map((key, idx) => (
                      <Area
                        key={key}
                        type="monotone"
                        dataKey={key}
                        name={key}
                        stroke={PALETTE[idx % PALETTE.length]}
                        fillOpacity={1}
                        fill={`url(#grad-${idx})`}
                        strokeWidth={2}
                      />
                    ))}
                  </AreaChart>
                );

              case 'pie':
                const pieValueKey = yKeys[0] || columns[1];
                return (
                  <PieChart margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ paddingTop: 10 }} />
                    <Pie
                      data={formattedData}
                      dataKey={pieValueKey}
                      nameKey={xKey}
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      innerRadius={45}
                      paddingAngle={3}
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    >
                      {formattedData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={PALETTE[index % PALETTE.length]} />
                      ))}
                    </Pie>
                  </PieChart>
                );

              case 'bar':
              default:
                return (
                  <BarChart data={formattedData} margin={{ top: 15, right: 25, left: 0, bottom: 25 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis
                      dataKey={xKey}
                      stroke="#94a3b8"
                      fontSize={12}
                      tickLine={false}
                      angle={-20}
                      textAnchor="end"
                    />
                    <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ paddingTop: 10 }} />
                    {yKeys.map((key, idx) => (
                      <Bar
                        key={key}
                        dataKey={key}
                        name={key}
                        fill={PALETTE[idx % PALETTE.length]}
                        radius={[4, 4, 0, 0]}
                        maxBarSize={50}
                      />
                    ))}
                  </BarChart>
                );
            }
          })()}
        </ResponsiveContainer>
      </div>
    </div>
  );
};
