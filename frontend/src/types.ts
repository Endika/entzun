export interface ReportData {
  transcript: string;
  report: string;
  visualization?: VisualizationData;
}

export interface VisualizationData {
  type: 'mindmap' | 'circleDiagram';
  nodes: Node[];
  links: Link[];
}

export interface Node {
  id: string;
  name: string;
  group?: number;
  value?: number;
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
  children?: Node[];
  depth?: number;
  height?: number;
  parent?: Node;
  data?: any;
}

export interface Link {
  source: string | Node;
  target: string | Node;
  value?: number;
}

export interface AudioRecorderProps {
  setReport: (report: ReportData | null) => void;
  setIsLoading: (isLoading: boolean) => void;
}

export interface AudioUploaderProps {
  setReport: (report: ReportData | null) => void;
  setIsLoading: (isLoading: boolean) => void;
}

export interface VisualizationPanelProps {
  report: ReportData | null;
  isLoading: boolean;
} 