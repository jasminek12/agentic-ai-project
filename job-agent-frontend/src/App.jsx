import { useMemo, useState } from 'react'
import './App.css'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || 'http://127.0.0.1:8000'

async function readErrorMessage(response, fallback) {
  try {
    const data = await response.json()
    if (typeof data?.error === 'string') {
      return data.error
    }
  } catch {
    // Ignore parse errors and use fallback.
  }
  return fallback
}

function App() {
  const [activeTab, setActiveTab] = useState('resume')

  const [resumeText, setResumeText] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [resumeError, setResumeError] = useState('')
  const [resumeSuccess, setResumeSuccess] = useState('')
  const [isTailoring, setIsTailoring] = useState(false)

  const [mode, setMode] = useState('behavioral')
  const [sessionId, setSessionId] = useState('session-1')
  const [interviewJobDescription, setInterviewJobDescription] = useState('')
  const [interviewResume, setInterviewResume] = useState('')
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [currentAnswer, setCurrentAnswer] = useState('')
  const [lastScore, setLastScore] = useState(null)
  const [lastFeedback, setLastFeedback] = useState('')
  const [interviewError, setInterviewError] = useState('')
  const [isStartingInterview, setIsStartingInterview] = useState(false)
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false)

  const canSubmitAnswer = useMemo(() => {
    return Boolean(currentQuestion) && currentAnswer.trim().length > 0
  }, [currentAnswer, currentQuestion])

  const handleTailorResume = async (event) => {
    event.preventDefault()
    setResumeError('')
    setResumeSuccess('')

    if (!resumeText.trim() || !jobDescription.trim()) {
      setResumeError('Resume text and job description are required.')
      return
    }

    setIsTailoring(true)
    try {
      const response = await fetch(`${API_BASE_URL}/tailor-resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resume_text: resumeText,
          job_description: jobDescription,
        }),
      })

      if (!response.ok) {
        const message = await readErrorMessage(response, 'Failed to tailor resume.')
        throw new Error(message)
      }

      const blob = await response.blob()
      const objectUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = `tailored_resume_${Date.now()}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(objectUrl)

      setResumeSuccess('Tailored resume generated. PDF download started.')
    } catch (error) {
      setResumeError(error.message || 'Failed to tailor resume.')
    } finally {
      setIsTailoring(false)
    }
  }

  const handleStartInterview = async (event) => {
    event.preventDefault()
    setInterviewError('')
    setLastScore(null)
    setLastFeedback('')
    setCurrentQuestion('')
    setCurrentAnswer('')

    if (!interviewJobDescription.trim() || !interviewResume.trim() || !sessionId.trim()) {
      setInterviewError('Mode, session ID, job description, and resume are required.')
      return
    }

    setIsStartingInterview(true)
    try {
      const response = await fetch(`${API_BASE_URL}/start-interview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode,
          session_id: sessionId,
          job_description: interviewJobDescription,
          resume: interviewResume,
        }),
      })

      if (!response.ok) {
        const message = await readErrorMessage(response, 'Failed to start interview.')
        throw new Error(message)
      }

      const data = await response.json()
      setCurrentQuestion(data.question || '')
    } catch (error) {
      setInterviewError(error.message || 'Failed to start interview.')
    } finally {
      setIsStartingInterview(false)
    }
  }

  const handleSubmitAnswer = async (event) => {
    event.preventDefault()
    setInterviewError('')

    if (!canSubmitAnswer) {
      setInterviewError('Please enter an answer before submitting.')
      return
    }

    setIsSubmittingAnswer(true)
    try {
      const response = await fetch(`${API_BASE_URL}/submit-answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          answer: currentAnswer,
          session_id: sessionId,
        }),
      })

      if (!response.ok) {
        const message = await readErrorMessage(response, 'Failed to submit answer.')
        throw new Error(message)
      }

      const data = await response.json()
      setLastScore(data.score ?? null)
      setLastFeedback(data.feedback ?? '')
      setCurrentQuestion(data.next_question || '')
      setCurrentAnswer('')
    } catch (error) {
      setInterviewError(error.message || 'Failed to submit answer.')
    } finally {
      setIsSubmittingAnswer(false)
    }
  }

  return (
    <div className="app">
      <header className="app__header">
        <h1>Job Agent Frontend</h1>
        <p>Frontend for resume tailoring and adaptive interview practice.</p>
        <p className="muted">
          Backend: <code>{API_BASE_URL}</code>
        </p>
      </header>

      <nav className="tabs" aria-label="Feature tabs">
        <button
          type="button"
          className={activeTab === 'resume' ? 'tab tab--active' : 'tab'}
          onClick={() => setActiveTab('resume')}
        >
          Tailor Resume
        </button>
        <button
          type="button"
          className={activeTab === 'interview' ? 'tab tab--active' : 'tab'}
          onClick={() => setActiveTab('interview')}
        >
          Interview Simulator
        </button>
      </nav>

      {activeTab === 'resume' ? (
        <section className="panel">
          <h2>Generate Tailored Resume PDF</h2>
          <form onSubmit={handleTailorResume} className="form">
            <label>
              Resume Text
              <textarea
                value={resumeText}
                onChange={(event) => setResumeText(event.target.value)}
                rows={10}
                placeholder="Paste your current resume text..."
                required
              />
            </label>

            <label>
              Job Description
              <textarea
                value={jobDescription}
                onChange={(event) => setJobDescription(event.target.value)}
                rows={10}
                placeholder="Paste the target job description..."
                required
              />
            </label>

            <button type="submit" disabled={isTailoring}>
              {isTailoring ? 'Generating PDF...' : 'Tailor Resume'}
            </button>

            {resumeError ? <p className="message message--error">{resumeError}</p> : null}
            {resumeSuccess ? <p className="message message--success">{resumeSuccess}</p> : null}
          </form>
        </section>
      ) : (
        <section className="panel">
          <h2>Adaptive Interview Session</h2>
          <form onSubmit={handleStartInterview} className="form">
            <div className="row">
              <label>
                Interview Mode
                <select value={mode} onChange={(event) => setMode(event.target.value)} required>
                  <option value="behavioral">Behavioral</option>
                  <option value="technical">Technical</option>
                </select>
              </label>

              <label>
                Session ID
                <input
                  type="text"
                  value={sessionId}
                  onChange={(event) => setSessionId(event.target.value)}
                  placeholder="user_123_session_1"
                  required
                />
              </label>
            </div>

            <label>
              Job Description
              <textarea
                value={interviewJobDescription}
                onChange={(event) => setInterviewJobDescription(event.target.value)}
                rows={8}
                placeholder="Paste the target job description..."
                required
              />
            </label>

            <label>
              Resume Text
              <textarea
                value={interviewResume}
                onChange={(event) => setInterviewResume(event.target.value)}
                rows={8}
                placeholder="Paste your resume text..."
                required
              />
            </label>

            <button type="submit" disabled={isStartingInterview}>
              {isStartingInterview ? 'Starting Interview...' : 'Start Interview'}
            </button>
          </form>

          {currentQuestion ? (
            <div className="question-card">
              <h3>Current Question</h3>
              <p>{currentQuestion}</p>

              <form onSubmit={handleSubmitAnswer} className="form">
                <label>
                  Your Answer
                  <textarea
                    value={currentAnswer}
                    onChange={(event) => setCurrentAnswer(event.target.value)}
                    rows={6}
                    placeholder="Write your interview answer..."
                    required
                  />
                </label>
                <button type="submit" disabled={isSubmittingAnswer}>
                  {isSubmittingAnswer ? 'Submitting...' : 'Submit Answer'}
                </button>
              </form>

              {lastScore !== null ? (
                <p className="message message--info">Score: {lastScore} / 10</p>
              ) : null}
              {lastFeedback ? <p className="message message--success">{lastFeedback}</p> : null}
            </div>
          ) : null}

          {interviewError ? <p className="message message--error">{interviewError}</p> : null}
        </section>
      )}
    </div>
  )
}

export default App
