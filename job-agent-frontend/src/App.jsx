import { useEffect, useMemo, useState } from 'react'
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

function toWordCount(text) {
  return text.trim() ? text.trim().split(/\s+/).length : 0
}

function toTitleCase(phrase) {
  if (!phrase || !String(phrase).trim()) {
    return ''
  }
  return String(phrase)
    .trim()
    .split(/\s+/)
    .map((word) => {
      if (!word) {
        return ''
      }
      if (word.length === 1) {
        return word.toUpperCase()
      }
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
    })
    .join(' ')
}

function getScoreLabel(score) {
  if (score >= 8) return 'Strong'
  if (score >= 6) return 'Promising'
  return 'Needs work'
}

function extractKeywords(text) {
  const stopWords = new Set([
    'the',
    'and',
    'for',
    'with',
    'you',
    'your',
    'that',
    'from',
    'this',
    'have',
    'are',
    'our',
    'will',
    'into',
    'using',
    'their',
    'about',
    'role',
  ])

  const words = text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((word) => word.length > 3 && !stopWords.has(word))

  const counts = words.reduce((acc, word) => {
    acc[word] = (acc[word] || 0) + 1
    return acc
  }, {})

  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([word]) => word)
}

function parseBullets(text) {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.startsWith('-') || line.startsWith('*'))
    .slice(0, 3)
}

function computeWeakAreas(answerText, feedbackText, score) {
  const lowerAnswer = answerText.toLowerCase()
  const lowerFeedback = feedbackText.toLowerCase()
  const weakAreas = []

  if (!/\d/.test(answerText) || lowerFeedback.includes('measurable')) {
    weakAreas.push('quantification')
  }
  if (answerText.length < 220 || lowerFeedback.includes('detail')) {
    weakAreas.push('depth')
  }
  if (
    !lowerAnswer.includes('situation') &&
    !lowerAnswer.includes('task') &&
    !lowerAnswer.includes('action') &&
    !lowerAnswer.includes('result')
  ) {
    weakAreas.push('star_framework')
  }
  if (score !== null && score < 7) {
    weakAreas.push('clarity')
  }
  return Array.from(new Set(weakAreas))
}

function buildOutreachMessage({
  messageType,
  channel,
  recipientName,
  company,
  role,
  senderName,
  notes,
  tone,
}) {
  const warm = tone === 'warm'
  const concise = tone === 'concise'
  const greetName = recipientName.trim()
  const greetDisplay = greetName ? toTitleCase(greetName) : ''
  const greeting = greetDisplay
    ? warm
      ? `Hi ${greetDisplay},`
      : `Hello ${greetDisplay},`
    : warm
      ? 'Hi there,'
      : 'Hello,'

  const companyLine = company.trim() ? toTitleCase(company.trim()) : 'your organization'
  const roleForBody = role.trim() ? toTitleCase(role.trim()) : ''
  const roleLine = roleForBody ? `the ${roleForBody} role` : 'the opportunity'
  const sender = senderName.trim() ? toTitleCase(senderName.trim()) : 'Your name'

  let core = ''
  switch (messageType) {
    case 'follow_up':
      core = `I am writing to follow up on my application for ${roleLine}${company.trim() ? ` at ${companyLine}` : ''}. I remain very interested and would welcome any update when convenient.`
      break
    case 'thank_you':
      core = `Thank you for your time${greetName ? '' : ' today'} discussing ${roleLine}${company.trim() ? ` at ${companyLine}` : ''}. I appreciated learning more about the team and priorities, and I am even more enthusiastic about the possibility of contributing.`
      break
    case 'cold':
      core = `I am reaching out because I am interested in ${roleLine}${company.trim() ? ` at ${companyLine}` : ''}. I believe my experience aligns well with what you are looking for, and I would value the chance to connect briefly.`
      break
    case 'connection':
      core = `I would like to connect${company.trim() ? ` regarding opportunities at ${companyLine}` : ''}${roleForBody ? `, particularly the ${roleForBody} role` : ''}. I would be glad to share a bit about my background if helpful.`
      break
    case 'schedule':
      core = `I would appreciate a brief conversation about ${roleLine}${company.trim() ? ` at ${companyLine}` : ''}. I am flexible on timing and happy to adapt to your calendar.`
      break
    default:
      core = `I am writing regarding ${roleLine}${company.trim() ? ` at ${companyLine}` : ''}.`
  }

  let extra = ''
  if (notes.trim()) {
    extra = concise
      ? `\n\nBrief context: ${notes.trim().split('\n')[0].slice(0, 280)}${notes.trim().length > 280 ? '…' : ''}`
      : `\n\nA few points I would highlight:\n${notes
          .trim()
          .split('\n')
          .map((line) => (line.trim() ? `• ${line.trim()}` : ''))
          .filter(Boolean)
          .join('\n')}`
  }

  const closing = warm
    ? `Warm regards,\n${sender}`
    : concise
      ? `Best,\n${sender}`
      : `Sincerely,\n${sender}`

  let full = `${greeting}\n\n${core}${extra}\n\n${closing}`

  if (channel === 'linkedin') {
    const shortCore = core.replace(/\n+/g, ' ').slice(0, 320)
    const shortExtra = notes.trim()
      ? ` ${notes.trim().split('\n')[0].slice(0, 120)}${notes.trim().length > 120 ? '…' : ''}`
      : ''
    full = `${greeting}\n\n${shortCore}${shortExtra}\n\n${closing.replace(/\n/g, ' ')}`
  }

  return full.trim()
}

function App() {
  const [userName, setUserName] = useState('')
  const [hasEnteredName, setHasEnteredName] = useState(false)
  const [nameFormValue, setNameFormValue] = useState('')
  const [activeTab, setActiveTab] = useState('resume')

  const [resumeText, setResumeText] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [resumeError, setResumeError] = useState('')
  const [resumeSuccess, setResumeSuccess] = useState('')
  const [isTailoring, setIsTailoring] = useState(false)
  const [resumeDiffPreview, setResumeDiffPreview] = useState([])

  const [mode, setMode] = useState('behavioral')
  const [sessionId, setSessionId] = useState('session-1')
  const [interviewJobDescription, setInterviewJobDescription] = useState('')
  const [interviewResume, setInterviewResume] = useState('')
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [currentAnswer, setCurrentAnswer] = useState('')
  const [lastScore, setLastScore] = useState(null)
  const [lastFeedback, setLastFeedback] = useState('')
  const [answerHistory, setAnswerHistory] = useState([])
  const [interviewError, setInterviewError] = useState('')
  const [isStartingInterview, setIsStartingInterview] = useState(false)
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false)
  const [goalInput, setGoalInput] = useState('')
  const [agentGoal, setAgentGoal] = useState('')
  const [goalSubtasks, setGoalSubtasks] = useState([])
  const [planPhase, setPlanPhase] = useState('idle')
  const [weakAreasMemory, setWeakAreasMemory] = useState([])

  const [outreachMessageType, setOutreachMessageType] = useState('follow_up')
  const [outreachChannel, setOutreachChannel] = useState('email')
  const [outreachTone, setOutreachTone] = useState('professional')
  const [outreachRecipientName, setOutreachRecipientName] = useState('')
  const [outreachCompany, setOutreachCompany] = useState('')
  const [outreachRole, setOutreachRole] = useState('')
  const [outreachNotes, setOutreachNotes] = useState('')
  const [framedMessage, setFramedMessage] = useState('')
  const [outreachCopyNotice, setOutreachCopyNotice] = useState('')
  const [outreachError, setOutreachError] = useState('')
  const [isFramingOutreach, setIsFramingOutreach] = useState(false)
  const [outreachLlmMeta, setOutreachLlmMeta] = useState(null)

  useEffect(() => {
    const savedName = window.localStorage.getItem('aih-user-name')?.trim() || ''
    if (savedName) {
      setNameFormValue(savedName)
    }

    const savedWeakAreas = window.localStorage.getItem('aih-weak-areas')
    if (savedWeakAreas) {
      try {
        const parsed = JSON.parse(savedWeakAreas)
        if (Array.isArray(parsed)) {
          setWeakAreasMemory(parsed)
        }
      } catch {
        // Ignore malformed local storage values.
      }
    }
  }, [])

  useEffect(() => {
    window.localStorage.setItem('aih-weak-areas', JSON.stringify(weakAreasMemory))
  }, [weakAreasMemory])

  const friendlyGreeting = useMemo(() => {
    const friendlyLines = [
      `Welcome back, ${userName}!`,
      `Good to see you, ${userName}.`,
      `Ready for another strong interview session, ${userName}?`,
    ]

    if (!userName) {
      return ''
    }

    const today = new Date().getDate()
    return friendlyLines[today % friendlyLines.length]
  }, [userName])

  const friendlyFact = useMemo(() => {
    const facts = [
      'Tip: concise STAR examples usually make behavioral answers more memorable.',
      'Tip: matching resume keywords to the job description can improve recruiter scans.',
      'Tip: technical answers are stronger when you explain trade-offs, not just solutions.',
      'Tip: saying your impact in numbers often makes accomplishments clearer.',
    ]
    const dayOfWeek = new Date().getDay()
    return facts[dayOfWeek % facts.length]
  }, [])

  const canSubmitAnswer = useMemo(() => {
    return Boolean(currentQuestion) && currentAnswer.trim().length > 0
  }, [currentAnswer, currentQuestion])

  const resumeWordCount = useMemo(() => toWordCount(resumeText), [resumeText])
  const jdWordCount = useMemo(() => toWordCount(jobDescription), [jobDescription])
  const interviewResumeWordCount = useMemo(() => toWordCount(interviewResume), [interviewResume])
  const interviewJdWordCount = useMemo(() => toWordCount(interviewJobDescription), [interviewJobDescription])
  const answerWordCount = useMemo(() => toWordCount(currentAnswer), [currentAnswer])
  const outreachNotesWordCount = useMemo(() => toWordCount(outreachNotes), [outreachNotes])

  const readinessScore = useMemo(() => {
    if (activeTab === 'outreach') {
      let score = 0
      if (outreachRecipientName.trim() || outreachCompany.trim()) score += 35
      if (outreachRole.trim()) score += 25
      if (outreachNotesWordCount >= 15) score += 25
      if (framedMessage.trim()) score += 15
      return Math.min(score, 100)
    }
    let score = 0
    if (interviewResumeWordCount >= 120) score += 30
    if (interviewJdWordCount >= 80) score += 30
    if (currentQuestion) score += 15
    if (answerWordCount >= 50) score += 25
    return Math.min(score, 100)
  }, [
    activeTab,
    answerWordCount,
    currentQuestion,
    framedMessage,
    interviewJdWordCount,
    interviewResumeWordCount,
    outreachCompany,
    outreachNotesWordCount,
    outreachRecipientName,
    outreachRole,
  ])

  const dynamicInsights = useMemo(() => {
    const insights = []

    if (activeTab === 'outreach') {
      insights.push(
        !outreachRecipientName.trim() && !outreachCompany.trim()
          ? 'Add a recipient name or company so the greeting and context feel personal.'
          : 'Recipient context looks good for a tailored opening.'
      )
      insights.push(
        !outreachRole.trim()
          ? 'Specify the role or opportunity so the message stays focused.'
          : 'Role is set — the agent can align the ask with that position.'
      )
      insights.push(
        outreachChannel === 'linkedin'
          ? 'LinkedIn mode keeps the draft shorter; use notes for one sharp value prop.'
          : 'Email mode supports a fuller structure with bullet context.'
      )
      return insights
    }

    if (activeTab === 'resume') {
      insights.push(
        resumeWordCount < 120
          ? 'Your resume text is short. Add impact bullets with measurable outcomes.'
          : 'Resume length looks solid for tailoring.'
      )
      insights.push(
        jdWordCount < 80
          ? 'Job description is brief. Paste the full posting for better tailoring.'
          : 'Job description has enough context for targeted matching.'
      )
      return insights
    }

    if (activeTab === 'interview') {
      insights.push(
        readinessScore >= 70
          ? 'You are interview-ready. Submit your answer with confident STAR framing.'
          : 'Prep is in progress. Add more resume/job detail to improve question quality.'
      )
      insights.push(
        answerWordCount < 45
          ? 'Your current answer is short. Aim for 60-120 words and include outcomes.'
          : 'Answer length looks good. Consider adding one metric to strengthen impact.'
      )
    }
    return insights
  }, [
    activeTab,
    answerWordCount,
    jdWordCount,
    outreachChannel,
    outreachCompany,
    outreachRecipientName,
    outreachRole,
    readinessScore,
    resumeWordCount,
  ])

  const confidenceCards = useMemo(() => {
    if (activeTab === 'outreach') {
      const hasAudience = Boolean(outreachRecipientName.trim() || outreachCompany.trim())
      return [
        {
          title: 'Message fit',
          confidence: hasAudience && outreachRole.trim() ? 'High' : 'Medium',
          rationale: hasAudience
            ? outreachRole.trim()
              ? 'Purpose, audience, and role are defined — strong basis for a professional draft.'
              : 'Audience is set; adding the role sharpens the ask.'
            : 'Add recipient or company so the agent can personalize the opening.',
        },
        {
          title: 'Channel appropriateness',
          confidence: outreachChannel === 'linkedin' ? 'High' : 'High',
          rationale:
            outreachChannel === 'linkedin'
              ? 'Draft will stay concise for InMail or connection-style messages.'
              : 'Draft uses a standard email structure suitable for recruiters and hiring managers.',
        },
      ]
    }
    if (activeTab === 'resume') {
      const keywordCount = extractKeywords(jobDescription).length
      return [
        {
          title: 'Keyword alignment',
          confidence: keywordCount >= 4 ? 'High' : 'Medium',
          rationale:
            keywordCount >= 4
              ? 'The job description includes enough repeated terms for targeting.'
              : 'Add full job posting text so the agent can map stronger keywords.',
        },
        {
          title: 'Resume tailoring quality',
          confidence: resumeWordCount >= 120 ? 'High' : 'Low',
          rationale:
            resumeWordCount >= 120
              ? 'Resume has enough detail for meaningful rewrite suggestions.'
              : 'Resume input is short; richer bullets produce better tailored output.',
        },
      ]
    }

    if (activeTab === 'interview') {
      return [
        {
          title: 'Answer quality prediction',
          confidence: answerWordCount >= 60 ? 'High' : 'Medium',
          rationale:
            answerWordCount >= 60
              ? 'Current draft has enough depth for structured scoring.'
              : 'Short draft may limit scoring confidence and feedback detail.',
        },
        {
          title: 'Interview readiness',
          confidence: readinessScore >= 70 ? 'High' : 'Medium',
          rationale:
            readinessScore >= 70
              ? 'Inputs are complete and answer context is sufficiently detailed.'
              : 'Add more resume/JD detail to improve next-question relevance.',
        },
      ]
    }

    return []
  }, [
    activeTab,
    answerWordCount,
    jobDescription,
    outreachChannel,
    outreachCompany,
    outreachRecipientName,
    outreachRole,
    readinessScore,
    resumeWordCount,
  ])

  const interventionSuggestions = useMemo(() => {
    if (activeTab !== 'interview' || !currentQuestion) {
      return []
    }

    const suggestions = []
    if (answerWordCount < 45) {
      suggestions.push('Try a 4-part STAR answer: Situation, Task, Action, Result.')
    }
    if (!/\d/.test(currentAnswer)) {
      suggestions.push('Add one metric (%, time saved, revenue, users) to show impact.')
    }
    if (
      currentAnswer &&
      !/learned|improved|would/i.test(currentAnswer) &&
      currentAnswer.length > 50
    ) {
      suggestions.push('End with what you learned or improved after this experience.')
    }
    return suggestions
  }, [activeTab, answerWordCount, currentAnswer, currentQuestion])

  const prioritizedWeakAreas = useMemo(() => {
    if (!weakAreasMemory.length) {
      return []
    }

    const counts = weakAreasMemory.reduce((acc, item) => {
      acc[item] = (acc[item] || 0) + 1
      return acc
    }, {})

    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([area, count]) => ({ area, count }))
  }, [weakAreasMemory])

  const planSteps = useMemo(() => {
    if (activeTab === 'outreach') {
      const steps = [
        { key: 'intent', label: 'Clarify recipient & purpose' },
        { key: 'draft', label: 'Frame professional message' },
        { key: 'polish', label: 'Match tone to channel' },
        { key: 'ready', label: 'Copy into email or LinkedIn' },
      ]
      const hasAudience = Boolean(outreachRecipientName.trim() || outreachCompany.trim())
      const hasRole = Boolean(outreachRole.trim())
      let workingIndex = 0
      if (hasAudience && hasRole) workingIndex = 1
      if (framedMessage.trim()) workingIndex = 4
      else if (hasAudience && hasRole && outreachNotesWordCount >= 5) workingIndex = 2

      return steps.map((step, index) => {
        if (framedMessage.trim()) {
          return { ...step, status: 'done' }
        }
        if (index < workingIndex) {
          return { ...step, status: 'done' }
        }
        if (index === workingIndex) {
          return { ...step, status: 'working' }
        }
        return { ...step, status: 'pending' }
      })
    }

    const base = [
      { key: 'extract', label: 'Extract keywords' },
      { key: 'rewrite', label: 'Rewrite bullets' },
      { key: 'quantify', label: 'Quantify impact' },
      { key: 'export', label: 'Export PDF' },
    ]

    const currentIndexMap = {
      idle: -1,
      extract: 0,
      rewrite: 1,
      quantify: 2,
      export: 3,
      done: 4,
    }

    const activeIndex = currentIndexMap[planPhase] ?? -1
    return base.map((step, index) => {
      if (planPhase === 'done' || index < activeIndex) {
        return { ...step, status: 'done' }
      }
      if (index === activeIndex) {
        return { ...step, status: 'working' }
      }
      return { ...step, status: 'pending' }
    })
  }, [
    activeTab,
    framedMessage,
    outreachCompany,
    outreachNotesWordCount,
    outreachRecipientName,
    outreachRole,
    planPhase,
  ])

  const activitySteps = useMemo(() => {
    if (activeTab === 'outreach') {
      const hasBasics = Boolean(
        outreachRecipientName.trim() || outreachCompany.trim() || outreachRole.trim()
      )
      return [
        {
          label: 'Profile captured',
          status: hasEnteredName ? 'done' : 'pending',
        },
        {
          label: 'Outreach details entered',
          status: hasBasics ? 'done' : 'pending',
        },
        {
          label: 'Message framed',
          status: framedMessage.trim() ? 'done' : 'pending',
        },
        {
          label: 'Ready to send',
          status: framedMessage.trim() ? 'done' : 'pending',
        },
      ]
    }

    return [
      {
        label: 'Profile captured',
        status: hasEnteredName ? 'done' : 'pending',
      },
      {
        label: 'Inputs provided',
        status:
          activeTab === 'resume'
            ? resumeWordCount > 0 && jdWordCount > 0
              ? 'done'
              : 'pending'
            : interviewResumeWordCount > 0 && interviewJdWordCount > 0
              ? 'done'
              : 'pending',
      },
      {
        label: activeTab === 'resume' ? 'Resume tailored' : 'Interview started',
        status:
          activeTab === 'resume'
            ? isTailoring
              ? 'working'
              : resumeSuccess
                ? 'done'
                : 'pending'
            : isStartingInterview
              ? 'working'
              : currentQuestion
                ? 'done'
                : 'pending',
      },
      {
        label: activeTab === 'resume' ? 'Ready to download PDF' : 'Answer submitted',
        status:
          activeTab === 'resume'
            ? resumeSuccess
              ? 'done'
              : 'pending'
            : isSubmittingAnswer
              ? 'working'
              : answerHistory.length > 0
                ? 'done'
                : 'pending',
      },
    ]
  }, [
    activeTab,
    answerHistory.length,
    currentQuestion,
    framedMessage,
    hasEnteredName,
    interviewJdWordCount,
    interviewResumeWordCount,
    isStartingInterview,
    isSubmittingAnswer,
    isTailoring,
    jdWordCount,
    outreachCompany,
    outreachRecipientName,
    outreachRole,
    resumeSuccess,
    resumeWordCount,
  ])

  const handleEnterApp = (event) => {
    event.preventDefault()
    const trimmedName = nameFormValue.trim()
    if (!trimmedName) {
      return
    }

    setUserName(trimmedName)
    setHasEnteredName(true)
    window.localStorage.setItem('aih-user-name', trimmedName)
  }

  const handleTailorResume = async (event) => {
    event.preventDefault()
    setResumeError('')
    setResumeSuccess('')

    if (!resumeText.trim() || !jobDescription.trim()) {
      setResumeError('Resume text and job description are required.')
      return
    }

    setIsTailoring(true)
    setPlanPhase('extract')
    try {
      const keywords = extractKeywords(jobDescription)
      const bullets = parseBullets(resumeText)
      const preview = bullets.map((bullet, index) => {
        const keyword = keywords[index % (keywords.length || 1)] || 'impact'
        return {
          before: bullet,
          after: `${bullet.replace(/^[-*]\s*/, '- ')} Focused on ${keyword} outcomes and measurable delivery.`,
        }
      })
      setResumeDiffPreview(preview)
      setPlanPhase('rewrite')

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

      setPlanPhase('quantify')
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
      setPlanPhase('done')
    } catch (error) {
      setResumeError(error.message || 'Failed to tailor resume.')
      setPlanPhase('idle')
    } finally {
      setIsTailoring(false)
    }
  }

  const handleSetGoal = (event) => {
    event.preventDefault()
    const nextGoal = goalInput.trim()
    if (!nextGoal) {
      return
    }

    const generatedSubtasks = [
      `Analyze goal intent: ${nextGoal}`,
      'Create personalized interview strategy',
      'Track weak areas and adapt next prompts',
      'Mark session complete with score trend review',
    ].map((title, index) => ({
      id: `${Date.now()}-${index}`,
      title,
      done: false,
    }))

    setAgentGoal(nextGoal)
    setGoalSubtasks(generatedSubtasks)
  }

  const toggleSubtask = (id) => {
    setGoalSubtasks((prev) =>
      prev.map((task) => (task.id === id ? { ...task, done: !task.done } : task))
    )
  }

  const composeOutreach = async () => {
    setOutreachCopyNotice('')
    setOutreachError('')
    const hasContext = Boolean(
      outreachRole.trim() ||
        outreachCompany.trim() ||
        outreachRecipientName.trim() ||
        outreachNotes.trim()
    )
    if (!hasContext) {
      setOutreachError(
        'Add at least one of: role, company, recipient, or key points so the API can frame your message.'
      )
      return
    }

    setIsFramingOutreach(true)
    try {
      const response = await fetch(`${API_BASE_URL}/frame-message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_type: outreachMessageType,
          channel: outreachChannel,
          tone: outreachTone,
          sender_name: userName,
          recipient_name: outreachRecipientName,
          company: outreachCompany,
          role: outreachRole,
          notes: outreachNotes,
        }),
      })

      if (!response.ok) {
        const message = await readErrorMessage(response, 'Could not frame message.')
        throw new Error(message)
      }

      const data = await response.json()
      const rawConf = String(data.confidence || 'medium').toLowerCase()
      const confidenceLabel =
        rawConf === 'high' || rawConf === 'medium' || rawConf === 'low'
          ? rawConf.charAt(0).toUpperCase() + rawConf.slice(1)
          : 'Medium'
      setFramedMessage(data.message || '')
      setOutreachLlmMeta({
        confidence: confidenceLabel,
        rationale: typeof data.rationale === 'string' ? data.rationale : '',
      })
    } catch (error) {
      setOutreachLlmMeta(null)
      setFramedMessage(
        buildOutreachMessage({
          messageType: outreachMessageType,
          channel: outreachChannel,
          recipientName: outreachRecipientName,
          company: outreachCompany,
          role: outreachRole,
          senderName: userName,
          notes: outreachNotes,
          tone: outreachTone,
        })
      )
      setOutreachError(`${error.message || 'Request failed.'} Showing a local template draft instead.`)
    } finally {
      setIsFramingOutreach(false)
    }
  }

  const handleFrameOutreachMessage = (event) => {
    event.preventDefault()
    void composeOutreach()
  }

  const handleClearOutreachDraft = () => {
    setFramedMessage('')
    setOutreachCopyNotice('')
    setOutreachError('')
    setOutreachLlmMeta(null)
  }

  const handleCopyOutreach = async () => {
    if (!framedMessage.trim()) {
      return
    }
    try {
      await navigator.clipboard.writeText(framedMessage)
      setOutreachCopyNotice('Copied to clipboard.')
    } catch {
      setOutreachCopyNotice('Copy failed — select the text and copy manually.')
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
      const detectedWeakAreas = computeWeakAreas(currentAnswer, data.feedback ?? '', data.score ?? null)
      setWeakAreasMemory((prev) => [...detectedWeakAreas, ...prev].slice(0, 40))
      setAnswerHistory((prev) => [
        {
          score: data.score ?? null,
          feedback: data.feedback ?? '',
          answeredAt: new Date().toLocaleTimeString(),
        },
        ...prev,
      ])
      setCurrentQuestion(data.next_question || '')
      setCurrentAnswer('')
    } catch (error) {
      setInterviewError(error.message || 'Failed to submit answer.')
    } finally {
      setIsSubmittingAnswer(false)
    }
  }

  if (!hasEnteredName) {
    return (
      <div className="welcome-page">
        <section className="welcome-card">
          <h1>Welcome to Job Agent</h1>
          <p>Enter your name to continue to your interview prep workspace.</p>
          <form onSubmit={handleEnterApp} className="form">
            <label>
              Your Name
              <input
                type="text"
                value={nameFormValue}
                onChange={(event) => setNameFormValue(event.target.value)}
                placeholder="Enter your name"
                required
              />
            </label>
            <button type="submit">Enter App</button>
          </form>
        </section>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="app__header">
        <h1>Job Agent Frontend</h1>
        <div className="welcome-banner">
          <p className="welcome-banner__title">{friendlyGreeting}</p>
          <p className="muted">{friendlyFact}</p>
        </div>
        <div className="header-meta">
          <p className="muted">Session user: {userName}</p>
          <button
            type="button"
            className="button button--secondary"
            onClick={() => setHasEnteredName(false)}
          >
            Change name
          </button>
        </div>
        <p>Frontend for resume tailoring and adaptive interview practice.</p>
        <p className="muted">
          Backend: <code>{API_BASE_URL}</code>
        </p>
      </header>

      <section className="agentic-dashboard panel">
        <div className="stat-grid">
          <article className="stat-card">
            <p className="stat-card__label">Workflow Progress</p>
            <p className="stat-card__value">
              {activitySteps.filter((step) => step.status === 'done').length} / {activitySteps.length}
            </p>
          </article>
          <article className="stat-card">
            <p className="stat-card__label">Interview Readiness</p>
            <p className="stat-card__value">{readinessScore}%</p>
          </article>
          <article className="stat-card">
            <p className="stat-card__label">Latest Score</p>
            <p className="stat-card__value">
              {lastScore === null ? 'N/A' : `${lastScore}/10 (${getScoreLabel(lastScore)})`}
            </p>
          </article>
        </div>

        <div className="agentic-columns">
          <div>
            <h3>Agent Workflow</h3>
            <ul className="step-list">
              {activitySteps.map((step) => (
                <li key={step.label} className={`step step--${step.status}`}>
                  <span className="step__dot" />
                  <span>{step.label}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3>Live Agent Insights</h3>
            <ul className="insight-list">
              {dynamicInsights.map((insight) => (
                <li key={insight}>{insight}</li>
              ))}
            </ul>
          </div>
        </div>

        <div className="timeline-wrap">
          <h3>Autonomous Plan Timeline</h3>
          <ul className="step-list">
            {planSteps.map((step) => (
              <li key={step.key} className={`step step--${step.status}`}>
                <span className="step__dot" />
                <span>{step.label}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="agentic-columns">
          <div>
            <h3>Agent Confidence + Rationale</h3>
            <div className="confidence-grid">
              {confidenceCards.map((card) => (
                <article key={card.title} className="stat-card">
                  <p className="stat-card__label">
                    {card.title} - {card.confidence} confidence
                  </p>
                  <p>{card.rationale}</p>
                </article>
              ))}
            </div>
          </div>
          <div>
            <h3>Goal + Subtask Execution</h3>
            <form onSubmit={handleSetGoal} className="form">
              <label>
                Set Agent Goal
                <input
                  type="text"
                  value={goalInput}
                  onChange={(event) => setGoalInput(event.target.value)}
                  placeholder="e.g. Get PM-ready behavioral answers"
                />
              </label>
              <button type="submit" className="button button--secondary">
                Build subtasks
              </button>
            </form>
            {agentGoal ? <p className="muted">Current goal: {agentGoal}</p> : null}
            {goalSubtasks.length > 0 ? (
              <ul className="step-list">
                {goalSubtasks.map((task) => (
                  <li key={task.id} className={`step ${task.done ? 'step--done' : 'step--pending'}`}>
                    <input
                      type="checkbox"
                      checked={task.done}
                      onChange={() => toggleSubtask(task.id)}
                      aria-label={task.title}
                    />
                    <span>{task.title}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
      </section>

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
        <button
          type="button"
          className={activeTab === 'outreach' ? 'tab tab--active' : 'tab'}
          onClick={() => setActiveTab('outreach')}
        >
          Professional outreach
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

          {resumeDiffPreview.length > 0 ? (
            <div className="question-card">
              <h3>What Changed (Draft Preview)</h3>
              <ul className="history-list">
                {resumeDiffPreview.map((item, index) => (
                  <li key={`${item.before}-${index}`}>
                    <p>
                      <strong>Before:</strong> {item.before}
                    </p>
                    <p>
                      <strong>After:</strong> {item.after}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : activeTab === 'interview' ? (
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

              {interventionSuggestions.length > 0 ? (
                <div className="message message--info">
                  <p>
                    <strong>Agent intervention:</strong>
                  </p>
                  <ul className="insight-list">
                    {interventionSuggestions.map((suggestion) => (
                      <li key={suggestion}>{suggestion}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {lastScore !== null ? (
                <p className="message message--info">Score: {lastScore} / 10</p>
              ) : null}
              {lastFeedback ? <p className="message message--success">{lastFeedback}</p> : null}
            </div>
          ) : null}

          {answerHistory.length > 0 ? (
            <div className="question-card">
              <h3>Recent Answer Performance</h3>
              <ul className="history-list">
                {answerHistory.slice(0, 4).map((item, index) => (
                  <li key={`${item.answeredAt}-${index}`}>
                    <strong>{item.score ?? 'N/A'}/10</strong> at {item.answeredAt} -{' '}
                    {item.feedback || 'No feedback returned.'}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {prioritizedWeakAreas.length > 0 ? (
            <div className="question-card">
              <h3>Memory Across Sessions (Prioritized)</h3>
              <ul className="history-list">
                {prioritizedWeakAreas.map((entry) => (
                  <li key={entry.area}>
                    <strong>{entry.area}</strong> appeared {entry.count} times in recent sessions.
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {interviewError ? <p className="message message--error">{interviewError}</p> : null}
        </section>
      ) : (
        <section className="panel panel--outreach">
          <div className="outreach-hero">
            <div>
              <h2>Professional outreach</h2>
              <p className="outreach-hero__sub">
                Draft recruiter-ready emails or short LinkedIn messages via the API (Groq), with a local template if
                the server is unavailable. Sign-off uses your login name (
                {userName || 'add your name on the welcome screen'}).
              </p>
            </div>
          </div>

          {confidenceCards.length > 0 ? (
            <div className="outreach-rationale" aria-label="Agent guidance for this draft">
              {confidenceCards.map((card) => (
                <div key={card.title} className="outreach-rationale__chip">
                  <span className="outreach-rationale__badge">{card.confidence}</span>
                  <div>
                    <p className="outreach-rationale__title">{card.title}</p>
                    <p className="outreach-rationale__text">{card.rationale}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : null}

          {outreachLlmMeta ? (
            <p className="message message--info outreach-llm-banner">
              <strong>Model ({outreachLlmMeta.confidence} confidence):</strong> {outreachLlmMeta.rationale}
            </p>
          ) : null}

          {outreachError ? <p className="message message--error">{outreachError}</p> : null}

          <form onSubmit={handleFrameOutreachMessage} className="outreach-form-card form">
            <p className="outreach-form-section__label">Message setup</p>
            <div className="row row--three">
              <label>
                Message purpose
                <select
                  className="input-elevated"
                  value={outreachMessageType}
                  onChange={(event) => setOutreachMessageType(event.target.value)}
                >
                  <option value="follow_up">Application follow-up</option>
                  <option value="thank_you">Thank-you after interview</option>
                  <option value="cold">Cold outreach / interest</option>
                  <option value="connection">Connection / intro request</option>
                  <option value="schedule">Request a brief call</option>
                </select>
              </label>
              <label>
                Channel
                <select
                  className="input-elevated"
                  value={outreachChannel}
                  onChange={(event) => setOutreachChannel(event.target.value)}
                >
                  <option value="email">Email</option>
                  <option value="linkedin">LinkedIn (shorter)</option>
                </select>
              </label>
              <label>
                Tone
                <select
                  className="input-elevated"
                  value={outreachTone}
                  onChange={(event) => setOutreachTone(event.target.value)}
                >
                  <option value="professional">Professional</option>
                  <option value="warm">Warm</option>
                  <option value="concise">Concise</option>
                </select>
              </label>
            </div>

            <p className="outreach-form-section__label">Who & what</p>
            <div className="row">
              <label>
                Recipient (optional)
                <input
                  className="input-elevated"
                  type="text"
                  value={outreachRecipientName}
                  onChange={(event) => setOutreachRecipientName(event.target.value)}
                  placeholder="First Last"
                  autoComplete="name"
                />
              </label>
              <label>
                Company (optional)
                <input
                  className="input-elevated"
                  type="text"
                  value={outreachCompany}
                  onChange={(event) => setOutreachCompany(event.target.value)}
                  placeholder="Company name"
                />
              </label>
            </div>

            <label>
              Role or opportunity
              <input
                className="input-elevated"
                type="text"
                value={outreachRole}
                onChange={(event) => setOutreachRole(event.target.value)}
                placeholder="e.g. Software engineering intern"
              />
            </label>

            <label>
              Key points (optional)
              <textarea
                className="input-elevated"
                value={outreachNotes}
                onChange={(event) => setOutreachNotes(event.target.value)}
                rows={4}
                placeholder="One line per idea: stack, years of experience, link to work, shared connection…"
              />
            </label>

            <div className="outreach-form-actions">
              <button className="button button--primary" type="submit" disabled={isFramingOutreach}>
                {isFramingOutreach ? 'Framing…' : 'Frame message'}
              </button>
            </div>
          </form>

          <div className="outreach-draft-card">
            <div className="outreach-draft-header">
              <div>
                <h3 className="outreach-draft-title">Your draft</h3>
                <p className="muted outreach-draft-hint">Edit freely, then copy into your email or LinkedIn.</p>
              </div>
              <span className="outreach-pill">Editable</span>
            </div>
            <label className="label-plain">
              <span className="sr-only">Message draft</span>
              <textarea
                className="draft-output input-elevated"
                value={framedMessage}
                onChange={(event) => setFramedMessage(event.target.value)}
                rows={12}
                placeholder="Click “Frame message” to generate a professional draft, or type your own."
              />
            </label>
            <div className="outreach-toolbar">
              <button type="button" className="button button--primary" onClick={handleCopyOutreach}>
                Copy to clipboard
              </button>
              <button
                type="button"
                className="button button--secondary"
                disabled={isFramingOutreach}
                onClick={() => {
                  void composeOutreach()
                }}
              >
                Regenerate
              </button>
              <button type="button" className="button button--ghost" onClick={handleClearOutreachDraft}>
                Clear draft
              </button>
            </div>
            {outreachCopyNotice ? <p className="message message--success outreach-toast">{outreachCopyNotice}</p> : null}
          </div>
        </section>
      )}
    </div>
  )
}

export default App
