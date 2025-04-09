import React, { useEffect, useRef } from 'react';
import styled from 'styled-components';
import * as d3 from 'd3';
import { VisualizationPanelProps } from '../types';

const PanelContainer = styled.div`
  display: flex;
  flex-direction: column;
  width: 100%;
  padding: 2rem;
  border-radius: 8px;
  background-color: #1a1a1a;
`;

const VisualizationContainer = styled.div`
  width: 100%;
  height: 500px;
  margin-top: 1rem;
  border: 1px solid #333;
  border-radius: 8px;
  overflow: hidden;
`;

const TranscriptContainer = styled.div`
  margin-top: 2rem;
  padding: 1rem;
  background-color: #2a2a2a;
  border-radius: 8px;
  max-height: 200px;
  overflow-y: auto;
`;

const ReportContainer = styled.div`
  margin-top: 1rem;
  padding: 1rem;
  background-color: #2a2a2a;
  border-radius: 8px;
  max-height: 300px;
  overflow-y: auto;
`;

const LoadingContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  height: 500px;
  font-size: 1.5rem;
`;

const VisualizationPanel = ({ report, isLoading }: VisualizationPanelProps) => {
  const svgRef = useRef<SVGSVGElement | null>(null);

  // Simplified visualization effect - avoiding complex D3 for now
  useEffect(() => {
    if (!report || !report.visualization || !svgRef.current) return;

    try {
      // Clear previous visualization
      d3.select(svgRef.current).selectAll('*').remove();

      // Simple placeholder visualization
      const svg = d3.select(svgRef.current);
      const width = svgRef.current.clientWidth;
      const height = svgRef.current.clientHeight;
      
      // Draw a placeholder circle
      svg.append('circle')
        .attr('cx', width / 2)
        .attr('cy', height / 2)
        .attr('r', 100)
        .attr('fill', '#646cff')
        .attr('opacity', 0.6);
        
      // Add text
      svg.append('text')
        .attr('x', width / 2)
        .attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('fill', 'white')
        .text('Visualization will appear here');
    } catch (error) {
      console.error('Error rendering visualization:', error);
    }
  }, [report]);

  return (
    <PanelContainer>
      <h2>Visualization & Analysis</h2>
      
      {isLoading ? (
        <LoadingContainer>
          <p>Processing audio and generating report...</p>
        </LoadingContainer>
      ) : report ? (
        <>
          <VisualizationContainer>
            <svg 
              ref={svgRef} 
              width="100%" 
              height="100%"
            />
          </VisualizationContainer>
          
          <h3>Transcript</h3>
          <TranscriptContainer>
            <p>{report.transcript}</p>
          </TranscriptContainer>
          
          <h3>Report</h3>
          <ReportContainer>
            <p>{report.report}</p>
          </ReportContainer>
        </>
      ) : (
        <LoadingContainer>
          <p>Record or upload audio to generate a visualization</p>
        </LoadingContainer>
      )}
    </PanelContainer>
  );
};

export default VisualizationPanel; 