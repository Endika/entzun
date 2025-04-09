import { useState, useRef, useEffect } from 'react';
import styled from 'styled-components';
import axios from 'axios';
import { AudioRecorderProps } from '../types';

const RecorderContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  width: 100%;
  padding: 2rem;
  border-radius: 8px;
  background-color: #1a1a1a;
`;

const ButtonsContainer = styled.div`
  display: flex;
  gap: 1rem;
`;

const StatusIndicator = styled.div<{ isRecording: boolean }>`
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: ${props => props.isRecording ? 'red' : 'gray'};
  margin-right: 10px;
`;

const StatusContainer = styled.div`
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
`;

const AudioRecorder = ({ setReport, setIsLoading }: AudioRecorderProps) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioChunks, setAudioChunks] = useState<Blob[]>([]);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const timerRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recordingTimeRef = useRef<number>(0);

  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  useEffect(() => {
    console.log('recordingTime updated:', recordingTime);
    recordingTimeRef.current = recordingTime;
  }, [recordingTime]);

  const startRecording = async () => {
    try {
      setAudioChunks([]);
      setIsRecording(true);
      setRecordingTime(0);
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          setAudioChunks(prev => [...prev, e.data]);
          
          if (recordingTimeRef.current >= 30 && recordingTimeRef.current % 30 === 0) {
            sendAudioChunk([e.data]);
          }
        }
      };
      
      mediaRecorder.start(1000);
      
      timerRef.current = window.setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
    } catch (error) {
      console.error('Error starting recording:', error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
      }
      
      setIsRecording(false);
      
      if (audioChunks.length > 0) {
        sendAudioChunk(audioChunks);
      }
    }
  };

  const sendAudioChunk = async (chunks: Blob[]) => {
    try {
      setIsLoading(true);
      
      const audioBlob = new Blob(chunks, { type: 'audio/mp3' });
      const formData = new FormData();
      formData.append('audio', audioBlob);
      
      const response = await axios.post('http://localhost:8000/api/v1/transcription/stream', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        responseType: 'text',
      });
      
      const responseText = response.data;
      const transcriptMatch = responseText.match(/Transcript: ([\s\S]*?)\n\n/);
      const reportMatch = responseText.match(/Report: ([\s\S]*)/);
      
      if (transcriptMatch && reportMatch) {
        const transcript = transcriptMatch[1];
        const report = reportMatch[1];
        
        setReport({
          transcript,
          report,
          visualization: {
            type: 'mindmap',
            nodes: [
              { id: 'root', name: 'Transcript Summary' },
            ],
            links: [
            ]
          }
        });
      }
    } catch (error) {
      console.error('Error sending audio chunk:', error);
    } finally {
      setIsLoading(false);
    }
  };

  console.log('Timer reference:', timerRef.current);

  return (
    <RecorderContainer>
      <StatusContainer>
        <StatusIndicator isRecording={isRecording} />
        <span>
          {isRecording 
            ? `Recording: ${Math.floor(recordingTime / 30)}:${(recordingTime % 30).toString().padStart(2, '0')}` 
            : 'Ready to record'}
        </span>
      </StatusContainer>
      
      <ButtonsContainer>
        {!isRecording ? (
          <button onClick={startRecording}>Start Recording</button>
        ) : (
          <button onClick={stopRecording}>Stop Recording</button>
        )}
      </ButtonsContainer>
      
      <p>
        {isRecording 
          ? 'Audio is being processed every minute for continuous transcription and analysis.' 
          : 'Click Start Recording to begin capturing audio.'}
      </p>
    </RecorderContainer>
  );
};

export default AudioRecorder; 