import { useState } from 'react'
import styled from 'styled-components'
import AudioRecorder from './components/AudioRecorder'
import AudioUploader from './components/AudioUploader'
import VisualizationPanel from './components/VisualizationPanel'
import { ReportData } from './types'

const AppContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
`

const Header = styled.header`
  margin-bottom: 2rem;
  text-align: center;
`

const ContentContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2rem;
  width: 100%;
`

const Tabs = styled.div`
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
`

const Tab = styled.button<{ active: boolean }>`
  background-color: ${(props) => (props.active ? '#646cff' : '#1a1a1a')};
  color: white;
`

function App() {
  const [activeTab, setActiveTab] = useState<'record' | 'upload'>('record')
  const [report, setReport] = useState<ReportData | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  return (
    <AppContainer>
      <Header>
        <h1>Audio Transcription & Visualization</h1>
        <p>Record or upload audio to generate visualizations from transcribed content</p>
      </Header>

      <ContentContainer>
        <Tabs>
          <Tab 
            active={activeTab === 'record'} 
            onClick={() => setActiveTab('record')}
          >
            Record Audio
          </Tab>
          <Tab 
            active={activeTab === 'upload'} 
            onClick={() => setActiveTab('upload')}
          >
            Upload Audio
          </Tab>
        </Tabs>

        {activeTab === 'record' ? (
          <AudioRecorder 
            setReport={setReport}
            setIsLoading={setIsLoading}
          />
        ) : (
          <AudioUploader 
            setReport={setReport}
            setIsLoading={setIsLoading}
          />
        )}

        <VisualizationPanel 
          report={report}
          isLoading={isLoading}
        />
      </ContentContainer>
    </AppContainer>
  )
}

export default App 