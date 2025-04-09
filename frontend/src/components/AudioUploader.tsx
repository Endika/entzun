import { useState, useRef } from 'react';
import styled from 'styled-components';
import axios from 'axios';
import { AudioUploaderProps } from '../types';

const UploaderContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  width: 100%;
  padding: 2rem;
  border-radius: 8px;
  background-color: #1a1a1a;
`;

const FileInputContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  width: 100%;
`;

const FileInputLabel = styled.label`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  border: 2px dashed #646cff;
  border-radius: 8px;
  cursor: pointer;
  width: 100%;
  
  &:hover {
    border-color: #535bf2;
  }
`;

const FileInput = styled.input`
  display: none;
`;

const FileName = styled.div`
  margin-top: 1rem;
  font-size: 0.9rem;
  color: #888;
`;

const AudioUploader = ({ setReport, setIsLoading }: AudioUploaderProps) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      setIsLoading(true);

      const formData = new FormData();
      formData.append('audio', selectedFile);

      const response = await axios.post('/api/v1/transcription/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const { transcript, report } = response.data;
      
      setReport({
        transcript,
        report,
        visualization: {
          type: 'circleDiagram',
          nodes: [
            { id: 'root', name: 'Transcript Summary' },
          ],
          links: [
          ]
        }
      });
    } catch (error) {
      console.error('Error uploading audio:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <UploaderContainer>
      <FileInputContainer>
        <FileInputLabel 
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 4V16M12 16L8 12M12 16L16 12" stroke="#646cff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M4 20H20" stroke="#646cff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <p>Drag and drop an audio file or click to select</p>
          <FileInput 
            type="file" 
            accept="audio/*" 
            onChange={handleFileChange}
            ref={fileInputRef}
          />
          {selectedFile && (
            <FileName>
              Selected: {selectedFile.name}
            </FileName>
          )}
        </FileInputLabel>
      </FileInputContainer>

      <button 
        onClick={handleUpload}
        disabled={!selectedFile}
      >
        Upload and Process
      </button>

      <p>
        Upload an audio file to get a transcription and visual representation of the content.
      </p>
    </UploaderContainer>
  );
};

export default AudioUploader; 