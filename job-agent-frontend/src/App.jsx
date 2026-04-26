import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './App.css'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || 'http://127.0.0.1:8000'

const DRAFT_KEY = 'aih-workspace-draft'
const INTERVIEW_ARCHIVE_KEY = 'aih-interview-archive'
const SESSION_ID_KEY = 'aih-session-id'
const SESSION_COUNTER_KEY = 'aih-session-counter'
const ACCOUNT_KEY = 'aih-local-accounts-v2'

function readStoredAccounts() {
  if (typeof window === 'undefined') {
    return []
  }
  try {
    const raw = window.localStorage.getItem(ACCOUNT_KEY)
    if (!raw) {
      return []
    }
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) {
      return parsed
        .filter(
          (account) =>
            account &&
            typeof account === 'object' &&
            typeof account.name === 'string' &&
            typeof account.username === 'string' &&
            typeof account.password === 'string'
        )
        .map((account) => ({
          name: account.name.trim(),
          username: normalizeUsername(account.username),
          password: account.password,
        }))
    }
  } catch {
    // Ignore malformed account state.
  }
  return []
}

function writeStoredAccounts(accounts) {
  if (typeof window === 'undefined') {
    return
  }
  window.localStorage.setItem(ACCOUNT_KEY, JSON.stringify(accounts))
}

function isValidPassword(password) {
  return /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/.test(password)
}

function normalizeUsername(username) {
  return String(username || '').trim().toLowerCase()
}

function findStoredAccount(username) {
  return readStoredAccounts().find((account) => account.username === normalizeUsername(username)) || null
}

function getDraftStorageKey(username) {
  const normalized = normalizeUsername(username)
  return normalized ? `${DRAFT_KEY}-${normalized}` : DRAFT_KEY
}

function getInterviewArchiveStorageKey(username) {
  const normalized = normalizeUsername(username)
  return normalized ? `${INTERVIEW_ARCHIVE_KEY}-${normalized}` : INTERVIEW_ARCHIVE_KEY
}

function readInterviewArchive(username) {
  if (typeof window === 'undefined') {
    return []
  }
  try {
    const raw = window.localStorage.getItem(getInterviewArchiveStorageKey(username))
    if (!raw) {
      return []
    }
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      return []
    }
    return parsed
      .filter((session) => session && typeof session === 'object' && typeof session.sessionId === 'string')
      .map((session) => ({
        sessionId: session.sessionId,
        mode: session.mode === 'technical' ? 'technical' : 'behavioral',
        startedAt: typeof session.startedAt === 'string' ? session.startedAt : '',
        updatedAt: typeof session.updatedAt === 'string' ? session.updatedAt : '',
        entries: Array.isArray(session.entries)
          ? session.entries
              .filter((entry) => entry && typeof entry === 'object')
              .map((entry) => ({
                question: typeof entry.question === 'string' ? entry.question : '',
                answer: typeof entry.answer === 'string' ? entry.answer : '',
                score: typeof entry.score === 'number' ? entry.score : null,
                feedback: typeof entry.feedback === 'string' ? entry.feedback : '',
                rewrite: typeof entry.rewrite === 'string' ? entry.rewrite : '',
                answeredAt: typeof entry.answeredAt === 'string' ? entry.answeredAt : '',
              }))
          : [],
      }))
      .sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)))
  } catch {
    return []
  }
}

function writeInterviewArchive(username, archive) {
  if (typeof window === 'undefined') {
    return
  }
  try {
    window.localStorage.setItem(getInterviewArchiveStorageKey(username), JSON.stringify(archive))
  } catch {
    // Ignore quota/storage failures.
  }
}

function formatDateTime(value) {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return date.toLocaleString()
}

function isValidTab(tab) {
  return tab === 'resume' || tab === 'interview' || tab === 'outreach'
}

function parseSessionNumber(sessionId) {
  const match = /^session-(\d+)$/.exec(String(sessionId || '').trim())
  return match ? Number(match[1]) : null
}

function createSessionId() {
  if (typeof window === 'undefined') {
    return `session-${Date.now()}`
  }
  try {
    const rawCounter = window.localStorage.getItem(SESSION_COUNTER_KEY)
    const currentCounter = Number.parseInt(rawCounter || '0', 10)
    const nextCounter = Number.isFinite(currentCounter) && currentCounter > 0 ? currentCounter + 1 : 1
    window.localStorage.setItem(SESSION_COUNTER_KEY, String(nextCounter))
    return `session-${nextCounter}`
  } catch {
    return `session-${Date.now()}`
  }
}

function getInitialSessionId() {
  if (typeof window === 'undefined') {
    return 'session-1'
  }
  try {
    const existing = window.localStorage.getItem(SESSION_ID_KEY)?.trim()
    if (existing) {
      const numericId = parseSessionNumber(existing)
      if (numericId) {
        const storedCounter = Number.parseInt(window.localStorage.getItem(SESSION_COUNTER_KEY) || '0', 10)
        if (!Number.isFinite(storedCounter) || storedCounter < numericId) {
          window.localStorage.setItem(SESSION_COUNTER_KEY, String(numericId))
        }
      }
      return existing
    }
    const id = createSessionId()
    window.localStorage.setItem(SESSION_ID_KEY, id)
    return id
  } catch {
    return createSessionId()
  }
}

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

  let core
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

function formatTailoredResumeForCopy(data) {
  if (!data || typeof data !== 'object') {
    return ''
  }

  const lines = []
  const summary = typeof data.summary === 'string' ? data.summary.trim() : ''
  const experience = Array.isArray(data.experience) ? data.experience : []
  const skills = Array.isArray(data.skills) ? data.skills : []

  if (summary) {
    lines.push('SUMMARY')
    lines.push(summary)
    lines.push('')
  }

  if (experience.length > 0) {
    lines.push('EXPERIENCE')
    for (const item of experience) {
      const title = typeof item?.title === 'string' ? item.title.trim() : ''
      const company = typeof item?.company === 'string' ? item.company.trim() : ''
      const heading = [title, company].filter(Boolean).join(' - ')
      if (heading) {
        lines.push(heading)
      }
      const points = Array.isArray(item?.points) ? item.points : []
      for (const point of points) {
        if (typeof point === 'string' && point.trim()) {
          lines.push(`- ${point.trim()}`)
        }
      }
      lines.push('')
    }
  }

  if (skills.length > 0) {
    lines.push('SKILLS')
    lines.push(
      skills
        .filter((skill) => typeof skill === 'string' && skill.trim())
        .map((skill) => skill.trim())
        .join(', ')
    )
  }

  return lines.join('\n').trim()
}

function App() {
  const [userName, setUserName] = useState('')
  const [currentUsername, setCurrentUsername] = useState('')
  const [hasEnteredName, setHasEnteredName] = useState(false)
  const [authMode, setAuthMode] = useState('signin')
  const [nameFormValue, setNameFormValue] = useState('')
  const [usernameFormValue, setUsernameFormValue] = useState('')
  const [passwordFormValue, setPasswordFormValue] = useState('')
  const [confirmPasswordFormValue, setConfirmPasswordFormValue] = useState('')
  const [authMessage, setAuthMessage] = useState('')
  const [authMessageType, setAuthMessageType] = useState('info')
  const [accountMenuOpen, setAccountMenuOpen] = useState(false)
  const [profileNameDraft, setProfileNameDraft] = useState('')
  const [profileSaveNotice, setProfileSaveNotice] = useState('')
  const [activeTab, setActiveTab] = useState('resume')

  const [resumeText, setResumeText] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [resumeError, setResumeError] = useState('')
  const [resumeSuccess, setResumeSuccess] = useState('')
  const [isTailoring, setIsTailoring] = useState(false)
  const [resumeDiffPreview, setResumeDiffPreview] = useState([])
  const [tailoredResumeData, setTailoredResumeData] = useState(null)
  const [resumeCopyNotice, setResumeCopyNotice] = useState('')

  const [mode, setMode] = useState('behavioral')
  const [sessionId, setSessionId] = useState(getInitialSessionId)
  const [interviewJobDescription, setInterviewJobDescription] = useState('')
  const [interviewResume, setInterviewResume] = useState('')
  const [panelModeEnabled, setPanelModeEnabled] = useState(false)
  const [pressureRoundEnabled, setPressureRoundEnabled] = useState(false)
  const [questionCountMode, setQuestionCountMode] = useState('agent')
  const [customQuestionCount, setCustomQuestionCount] = useState('6')
  const [companyContext, setCompanyContext] = useState('')
  const [roleContext, setRoleContext] = useState('')
  const [interviewDate, setInterviewDate] = useState('')
  const [interviewViewActive, setInterviewViewActive] = useState(false)
  const [interviewStatusMessage, setInterviewStatusMessage] = useState('')
  const [interviewStage, setInterviewStage] = useState('session')
  const [targetQuestionCount, setTargetQuestionCount] = useState(0)
  const [answeredCount, setAnsweredCount] = useState(0)
  const [pendingNextQuestion, setPendingNextQuestion] = useState('')
  const [showFollowUpPreview, setShowFollowUpPreview] = useState(false)
  const [showNextQuestionPreview, setShowNextQuestionPreview] = useState(false)
  const [waitingForNextStep, setWaitingForNextStep] = useState(false)
  const [isAdvancingInterview, setIsAdvancingInterview] = useState(false)
  const [finalEvaluation, setFinalEvaluation] = useState('')
  const [interviewComplete, setInterviewComplete] = useState(false)
  const [questionTrail, setQuestionTrail] = useState([])
  const [questionTrailIndex, setQuestionTrailIndex] = useState(0)
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [currentAnswer, setCurrentAnswer] = useState('')
  const [lastScore, setLastScore] = useState(null)
  const [lastFeedback, setLastFeedback] = useState('')
  const [latestFollowUpQuestion, setLatestFollowUpQuestion] = useState('')
  const [latestCritique, setLatestCritique] = useState('')
  const [latestRewrite, setLatestRewrite] = useState('')
  const [isRewriteSpeaking, setIsRewriteSpeaking] = useState(false)
  const [isRewritePaused, setIsRewritePaused] = useState(false)
  const [rewriteSpeechProgress, setRewriteSpeechProgress] = useState(0)
  const [debriefActions, setDebriefActions] = useState([])
  const [nextRoundTarget, setNextRoundTarget] = useState('')
  const [curriculumPlan, setCurriculumPlan] = useState([])
  const [answerHistory, setAnswerHistory] = useState([])
  const [interviewError, setInterviewError] = useState('')
  const [isStartingInterview, setIsStartingInterview] = useState(false)
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false)
  const [goalInput, setGoalInput] = useState('')
  const [agentGoal, setAgentGoal] = useState('')
  const [goalSubtasks, setGoalSubtasks] = useState([])
  const [planPhase, setPlanPhase] = useState('idle')
  const [weakAreasMemory, setWeakAreasMemory] = useState([])
  const [interviewSessionsArchive, setInterviewSessionsArchive] = useState([])
  const [resumePromptAcknowledgedSessionId, setResumePromptAcknowledgedSessionId] = useState('')
  const [interviewHistoryPanelOpen, setInterviewHistoryPanelOpen] = useState(false)

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
  const [apiHealth, setApiHealth] = useState('checking')
  const rewriteUtteranceRef = useRef(null)
  const rewriteSpeechOffsetRef = useRef(0)
  const evaluationTimerRef = useRef(null)

  const applyWorkspaceDraft = useCallback((d) => {
    if (!d || d.v !== 1) {
      return
    }
    if (d.activeTab && isValidTab(d.activeTab)) {
      setActiveTab(d.activeTab)
    }
    if (d.resume) {
      if (typeof d.resume.resumeText === 'string') {
        setResumeText(d.resume.resumeText)
      }
      if (typeof d.resume.jobDescription === 'string') {
        setJobDescription(d.resume.jobDescription)
      }
      if (
        d.resume.planPhase === 'idle' ||
        d.resume.planPhase === 'extract' ||
        d.resume.planPhase === 'rewrite' ||
        d.resume.planPhase === 'quantify' ||
        d.resume.planPhase === 'export' ||
        d.resume.planPhase === 'done'
      ) {
        setPlanPhase(d.resume.planPhase)
      }
    }
    if (d.interview) {
      const iv = d.interview
      if (iv.mode === 'behavioral' || iv.mode === 'technical') {
        setMode(iv.mode)
      }
      if (typeof iv.sessionId === 'string' && iv.sessionId.trim()) {
        setSessionId(iv.sessionId.trim())
        try {
          window.localStorage.setItem(SESSION_ID_KEY, iv.sessionId.trim())
        } catch {
          // Ignore.
        }
      }
      if (typeof iv.interviewJobDescription === 'string') {
        setInterviewJobDescription(iv.interviewJobDescription)
      }
      if (typeof iv.interviewResume === 'string') {
        setInterviewResume(iv.interviewResume)
      }
      if (typeof iv.panelModeEnabled === 'boolean') {
        setPanelModeEnabled(iv.panelModeEnabled)
      }
      if (typeof iv.pressureRoundEnabled === 'boolean') {
        setPressureRoundEnabled(iv.pressureRoundEnabled)
      }
      if (iv.questionCountMode === 'agent' || iv.questionCountMode === 'custom') {
        setQuestionCountMode(iv.questionCountMode)
      }
      if (typeof iv.customQuestionCount === 'string') {
        setCustomQuestionCount(iv.customQuestionCount)
      }
      if (typeof iv.companyContext === 'string') {
        setCompanyContext(iv.companyContext)
      }
      if (typeof iv.roleContext === 'string') {
        setRoleContext(iv.roleContext)
      }
      if (typeof iv.interviewDate === 'string') {
        setInterviewDate(iv.interviewDate)
      }
      if (typeof iv.interviewViewActive === 'boolean') {
        setInterviewViewActive(false)
      }
      if (typeof iv.interviewStatusMessage === 'string') {
        setInterviewStatusMessage(iv.interviewStatusMessage)
      }
      if (typeof iv.targetQuestionCount === 'number') {
        setTargetQuestionCount(iv.targetQuestionCount)
      }
      if (typeof iv.answeredCount === 'number') {
        setAnsweredCount(iv.answeredCount)
      }
      if (typeof iv.pendingNextQuestion === 'string') {
        setPendingNextQuestion(iv.pendingNextQuestion)
      }
      if (typeof iv.waitingForNextStep === 'boolean') {
        setWaitingForNextStep(iv.waitingForNextStep)
      }
      if (typeof iv.finalEvaluation === 'string') {
        setFinalEvaluation(iv.finalEvaluation)
      }
      if (typeof iv.interviewComplete === 'boolean') {
        setInterviewComplete(iv.interviewComplete)
      }
      if (Array.isArray(iv.questionTrail)) {
        setQuestionTrail(iv.questionTrail.slice(0, 40))
      }
      if (typeof iv.questionTrailIndex === 'number') {
        setQuestionTrailIndex(iv.questionTrailIndex)
      }
      if (typeof iv.goalInput === 'string') {
        setGoalInput(iv.goalInput)
      }
      if (typeof iv.agentGoal === 'string') {
        setAgentGoal(iv.agentGoal)
      }
      if (Array.isArray(iv.goalSubtasks)) {
        setGoalSubtasks(iv.goalSubtasks)
      }
      if (typeof iv.currentQuestion === 'string') {
        setCurrentQuestion(iv.currentQuestion)
      }
      if (typeof iv.currentAnswer === 'string') {
        setCurrentAnswer(iv.currentAnswer)
      }
      if (Array.isArray(iv.answerHistory)) {
        setAnswerHistory(iv.answerHistory.slice(0, 8))
      }
      if (iv.lastScore === null || (typeof iv.lastScore === 'number' && !Number.isNaN(iv.lastScore))) {
        setLastScore(iv.lastScore)
      }
      if (typeof iv.lastFeedback === 'string') {
        setLastFeedback(iv.lastFeedback)
      }
      if (typeof iv.latestFollowUpQuestion === 'string') {
        setLatestFollowUpQuestion(iv.latestFollowUpQuestion)
      }
      if (typeof iv.latestCritique === 'string') {
        setLatestCritique(iv.latestCritique)
      }
      if (typeof iv.latestRewrite === 'string') {
        setLatestRewrite(iv.latestRewrite)
      }
      if (Array.isArray(iv.debriefActions)) {
        setDebriefActions(iv.debriefActions.slice(0, 3))
      }
      if (typeof iv.nextRoundTarget === 'string') {
        setNextRoundTarget(iv.nextRoundTarget)
      }
      if (Array.isArray(iv.curriculumPlan)) {
        setCurriculumPlan(iv.curriculumPlan.slice(0, 7))
      }
    }
    if (d.outreach) {
      const o = d.outreach
      if (['follow_up', 'thank_you', 'cold', 'connection', 'schedule'].includes(o.outreachMessageType)) {
        setOutreachMessageType(o.outreachMessageType)
      }
      if (o.outreachChannel === 'email' || o.outreachChannel === 'linkedin') {
        setOutreachChannel(o.outreachChannel)
      }
      if (o.outreachTone === 'professional' || o.outreachTone === 'warm' || o.outreachTone === 'concise') {
        setOutreachTone(o.outreachTone)
      }
      if (typeof o.outreachRecipientName === 'string') {
        setOutreachRecipientName(o.outreachRecipientName)
      }
      if (typeof o.outreachCompany === 'string') {
        setOutreachCompany(o.outreachCompany)
      }
      if (typeof o.outreachRole === 'string') {
        setOutreachRole(o.outreachRole)
      }
      if (typeof o.outreachNotes === 'string') {
        setOutreachNotes(o.outreachNotes)
      }
      if (typeof o.framedMessage === 'string') {
        setFramedMessage(o.framedMessage)
      }
      if (
        o.outreachLlmMeta &&
        typeof o.outreachLlmMeta === 'object' &&
        typeof o.outreachLlmMeta.confidence === 'string'
      ) {
        setOutreachLlmMeta({
          confidence: o.outreachLlmMeta.confidence,
          rationale: typeof o.outreachLlmMeta.rationale === 'string' ? o.outreachLlmMeta.rationale : '',
        })
      }
    }
  }, [])

  const resetWorkspaceState = useCallback(() => {
    setActiveTab('resume')
    setResumeText('')
    setJobDescription('')
    setResumeError('')
    setResumeSuccess('')
    setResumeDiffPreview([])
    setMode('behavioral')
    setSessionId(getInitialSessionId())
    setInterviewJobDescription('')
    setInterviewResume('')
    setPanelModeEnabled(false)
    setPressureRoundEnabled(false)
    setQuestionCountMode('agent')
    setCustomQuestionCount('6')
    setCompanyContext('')
    setRoleContext('')
    setInterviewDate('')
    setInterviewViewActive(false)
    setInterviewStatusMessage('')
    setInterviewStage('session')
    setTargetQuestionCount(0)
    setAnsweredCount(0)
    setPendingNextQuestion('')
    setShowFollowUpPreview(false)
    setShowNextQuestionPreview(false)
    setWaitingForNextStep(false)
    setIsAdvancingInterview(false)
    setFinalEvaluation('')
    setInterviewComplete(false)
    setQuestionTrail([])
    setQuestionTrailIndex(0)
    setCurrentQuestion('')
    setCurrentAnswer('')
    setLastScore(null)
    setLastFeedback('')
    setLatestFollowUpQuestion('')
    setLatestCritique('')
    setLatestRewrite('')
    setIsRewriteSpeaking(false)
    setIsRewritePaused(false)
    setRewriteSpeechProgress(0)
    setDebriefActions([])
    setNextRoundTarget('')
    setCurriculumPlan([])
    setResumePromptAcknowledgedSessionId('')
    setAnswerHistory([])
    setInterviewError('')
    setGoalInput('')
    setAgentGoal('')
    setGoalSubtasks([])
    setPlanPhase('idle')
    setOutreachMessageType('follow_up')
    setOutreachChannel('email')
    setOutreachTone('professional')
    setOutreachRecipientName('')
    setOutreachCompany('')
    setOutreachRole('')
    setOutreachNotes('')
    setFramedMessage('')
    setOutreachCopyNotice('')
    setOutreachError('')
    setOutreachLlmMeta(null)
  }, [])

  useEffect(() => {
    const savedAccounts = readStoredAccounts()
    if (savedAccounts.length > 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAuthMode('signin')
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAuthMessage('Use your username and password to sign in, or create a new account with a unique username.')
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAuthMessageType('info')
    } else {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAuthMode('signup')
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

    const h = (window.location.hash || '').replace(/^#/, '')
    if (isValidTab(h)) {
      setActiveTab(h)
    }
  }, [applyWorkspaceDraft])

  useEffect(() => {
    const onHashChange = () => {
      const h = (window.location.hash || '').replace(/^#/, '')
      if (isValidTab(h)) {
        setActiveTab(h)
      }
    }
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    if (userName) {
      setProfileNameDraft(userName)
    }
  }, [userName])

  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel()
      }
      if (evaluationTimerRef.current) {
        window.clearTimeout(evaluationTimerRef.current)
        evaluationTimerRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (!hasEnteredName) {
      return
    }
    if (!isValidTab(activeTab)) {
      return
    }
    const next = `#${activeTab}`
    if (window.location.hash !== next) {
      window.history.replaceState(null, '', next)
    }
  }, [activeTab, hasEnteredName])

  useEffect(() => {
    if (!hasEnteredName) {
      return
    }
    try {
      if (sessionId.trim()) {
        window.localStorage.setItem(SESSION_ID_KEY, sessionId.trim())
      }
    } catch {
      // Ignore quota errors.
    }
  }, [sessionId, hasEnteredName])

  useEffect(() => {
    if (!hasEnteredName || !currentUsername) {
      setInterviewSessionsArchive([])
      return
    }
    setInterviewSessionsArchive(readInterviewArchive(currentUsername))
  }, [currentUsername, hasEnteredName])

  useEffect(() => {
    let alive = true
    const ac = new AbortController()
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setApiHealth('checking')
    fetch(`${API_BASE_URL}/health`, { signal: ac.signal })
      .then((r) => {
        if (alive) {
          setApiHealth(r.ok ? 'ok' : 'error')
        }
      })
      .catch(() => {
        if (alive) {
          setApiHealth('error')
        }
      })
    return () => {
      alive = false
      ac.abort()
    }
  }, [])

  useEffect(() => {
    if (!hasEnteredName) {
      return
    }
    if (!currentUsername) {
      return
    }
    const t = setTimeout(() => {
      const payload = {
        v: 1,
        activeTab,
        resume: {
          resumeText,
          jobDescription,
          planPhase,
        },
        interview: {
          mode,
          sessionId,
          interviewJobDescription,
          interviewResume,
          panelModeEnabled,
          pressureRoundEnabled,
          questionCountMode,
          customQuestionCount,
          companyContext,
          roleContext,
          interviewDate,
          interviewViewActive,
          interviewStatusMessage,
          targetQuestionCount,
          answeredCount,
          pendingNextQuestion,
          waitingForNextStep,
          finalEvaluation,
          interviewComplete,
          questionTrail: questionTrail.slice(0, 40),
          questionTrailIndex,
          goalInput,
          agentGoal,
          goalSubtasks,
          currentQuestion,
          currentAnswer,
          answerHistory: answerHistory.slice(0, 8),
          lastScore,
          lastFeedback,
          latestFollowUpQuestion,
          latestCritique,
          latestRewrite,
          debriefActions: debriefActions.slice(0, 3),
          nextRoundTarget,
          curriculumPlan: curriculumPlan.slice(0, 7),
        },
        outreach: {
          outreachMessageType,
          outreachChannel,
          outreachTone,
          outreachRecipientName,
          outreachCompany,
          outreachRole,
          outreachNotes,
          framedMessage,
          outreachLlmMeta,
        },
      }
      try {
        window.localStorage.setItem(getDraftStorageKey(currentUsername), JSON.stringify(payload))
      } catch (err) {
        console.warn('Could not save workspace draft', err)
      }
    }, 550)
    return () => clearTimeout(t)
  }, [
    activeTab,
    hasEnteredName,
    currentUsername,
    resumeText,
    jobDescription,
    planPhase,
    mode,
    sessionId,
    interviewJobDescription,
    interviewResume,
    panelModeEnabled,
    pressureRoundEnabled,
    questionCountMode,
    customQuestionCount,
    companyContext,
    roleContext,
    interviewDate,
    interviewViewActive,
    interviewStatusMessage,
    targetQuestionCount,
    answeredCount,
    pendingNextQuestion,
    waitingForNextStep,
    finalEvaluation,
    interviewComplete,
    questionTrail,
    questionTrailIndex,
    goalInput,
    agentGoal,
    goalSubtasks,
    currentQuestion,
    currentAnswer,
    answerHistory,
    lastScore,
    lastFeedback,
    latestFollowUpQuestion,
    latestCritique,
    latestRewrite,
    debriefActions,
    nextRoundTarget,
    curriculumPlan,
    outreachMessageType,
    outreachChannel,
    outreachTone,
    outreachRecipientName,
    outreachCompany,
    outreachRole,
    outreachNotes,
    framedMessage,
    outreachLlmMeta,
  ])

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
  const speechSupported = useMemo(() => {
    return (
      typeof window !== 'undefined' &&
      'speechSynthesis' in window &&
      typeof window.SpeechSynthesisUtterance !== 'undefined'
    )
  }, [])
  const isViewingLatestQuestion = useMemo(() => {
    if (!questionTrail.length) {
      return true
    }
    return questionTrailIndex >= questionTrail.length - 1
  }, [questionTrail, questionTrailIndex])
  const displayedQuestion = useMemo(() => {
    if (!questionTrail.length) {
      return currentQuestion
    }
    return questionTrail[questionTrailIndex] || currentQuestion
  }, [currentQuestion, questionTrail, questionTrailIndex])

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
      { key: 'export', label: 'Prepare copyable output' },
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
        label: activeTab === 'resume' ? 'Ready to copy tailored resume' : 'Answer submitted',
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
  const completedActivitySteps = useMemo(
    () => activitySteps.filter((step) => step.status === 'done').length,
    [activitySteps]
  )
  const nextStepLabel = useMemo(() => {
    const nextPendingStep = activitySteps.find((step) => step.status !== 'done')
    return nextPendingStep ? nextPendingStep.label : 'All core steps are complete.'
  }, [activitySteps])
  const topInsights = useMemo(() => dynamicInsights.slice(0, 2), [dynamicInsights])
  const currentSessionArchiveEntry = useMemo(
    () => interviewSessionsArchive.find((session) => session.sessionId === sessionId) || null,
    [interviewSessionsArchive, sessionId]
  )
  const shouldPromptToResumeInterview =
    Boolean(currentQuestion || waitingForNextStep || (answeredCount > 0 && !interviewComplete)) &&
    !interviewViewActive &&
    sessionId !== resumePromptAcknowledgedSessionId
  const interviewTranscriptItems = useMemo(() => {
    const historyItems = answerHistory.map((item) => ({
      question: item.question || '',
      answer: item.answer || '',
      agentAnswer: item.rewrite || item.feedback || '',
      answeredAt: item.answeredAt || '',
    }))
    if (currentQuestion && !historyItems.some((item) => item.question === currentQuestion && !item.answer)) {
      historyItems.unshift({
        question: currentQuestion,
        answer: '',
        agentAnswer: '',
        answeredAt: '',
      })
    }
    return historyItems
  }, [answerHistory, currentQuestion])
  const agentLiveStatus = useMemo(() => {
    if (activeTab === 'resume') {
      if (isTailoring) {
        return { isRunning: true, text: 'Analyzing role keywords and rewriting resume bullets.' }
      }
      if (resumeSuccess || tailoredResumeData) {
        return { isRunning: false, text: 'Tailoring pass complete. Draft is ready to review.' }
      }
      return { isRunning: false, text: 'Waiting for resume and job description inputs.' }
    }
    if (activeTab === 'interview') {
      if (isStartingInterview) {
        return { isRunning: true, text: 'Preparing interview context and first prompt.' }
      }
      if (isSubmittingAnswer) {
        return { isRunning: true, text: 'Scoring answer and generating coaching feedback.' }
      }
      if (currentQuestion) {
        return { isRunning: false, text: 'Interview is active. Submit an answer to continue.' }
      }
      return { isRunning: false, text: 'Ready to start a new interview session.' }
    }
    if (isFramingOutreach) {
      return { isRunning: true, text: 'Drafting outreach message for selected tone and channel.' }
    }
    if (framedMessage.trim()) {
      return { isRunning: false, text: 'Outreach draft generated. Refine and copy when ready.' }
    }
    return { isRunning: false, text: 'Ready to frame a recruiter-ready outreach message.' }
  }, [
    activeTab,
    currentQuestion,
    framedMessage,
    isFramingOutreach,
    isStartingInterview,
    isSubmittingAnswer,
    isTailoring,
    resumeSuccess,
    tailoredResumeData,
  ])
  const recentAgentActions = useMemo(() => {
    if (activeTab === 'resume') {
      if (resumeSuccess || tailoredResumeData) {
        return [
          'Extracted role keywords from the job description.',
          'Rewrote experience bullets for stronger impact language.',
          'Prepared copy-ready tailored resume output.',
        ]
      }
      return [
        'Standing by for resume and job description context.',
        'Will map keywords to your strongest experience bullets.',
        'Will prioritize quantified outcomes during rewrite.',
      ]
    }
    if (activeTab === 'interview') {
      const latestAttempt = answerHistory[0]
      const latestScoreNote =
        latestAttempt && typeof latestAttempt.score === 'number'
          ? `Last score logged: ${latestAttempt.score}/10.`
          : 'No scored answer logged yet.'
      return [
        latestScoreNote,
        currentQuestion
          ? 'Current interview question is loaded and ready.'
          : 'Question queue will start after session initialization.',
        'Weak-spot feedback is tracked across recent sessions.',
      ]
    }
    return [
      framedMessage.trim()
        ? 'Generated an editable outreach draft aligned to your tone.'
        : 'Awaiting outreach inputs to draft message copy.',
      outreachCopyNotice ? 'Copied latest outreach draft to clipboard.' : 'Draft can be copied in one click after generation.',
      'Channel setting tunes message length for email vs LinkedIn.',
    ]
  }, [
    activeTab,
    answerHistory,
    currentQuestion,
    framedMessage,
    outreachCopyNotice,
    resumeSuccess,
    tailoredResumeData,
  ])

  const handleEnterApp = (event) => {
    event.preventDefault()
    const trimmedName = nameFormValue.trim()
    const trimmedUsername = normalizeUsername(usernameFormValue)
    const trimmedPassword = passwordFormValue.trim()
    const trimmedConfirmPassword = confirmPasswordFormValue.trim()
    const requiresName = authMode === 'signup'
    const requiresConfirm = authMode === 'signup' || authMode === 'forgot'
    if (
      !trimmedUsername ||
      !trimmedPassword ||
      (requiresName && !trimmedName) ||
      (requiresConfirm && !trimmedConfirmPassword)
    ) {
      setAuthMessage(
        authMode === 'signin'
          ? 'Username and password are required.'
          : authMode === 'signup'
            ? 'Name, username, password, and confirm password are required.'
            : 'Username, new password, and confirm password are required.'
      )
      setAuthMessageType('error')
      return
    }
    if (!isValidPassword(trimmedPassword)) {
      setAuthMessage(
        'Password must be at least 8 characters and include a lowercase letter, uppercase letter, and number.'
      )
      setAuthMessageType('error')
      return
    }

    const savedAccount = findStoredAccount(trimmedUsername)
    if (authMode === 'signup') {
      if (savedAccount) {
        setAuthMessage('That username is already taken. Choose a different username.')
        setAuthMessageType('error')
        return
      }
      if (trimmedPassword !== trimmedConfirmPassword) {
        setAuthMessage('Password and confirm password must match.')
        setAuthMessageType('error')
        return
      }
      const updatedAccounts = [
        ...readStoredAccounts(),
        { name: trimmedName, username: trimmedUsername, password: trimmedPassword },
      ]
      writeStoredAccounts(updatedAccounts)
      setAuthMessage('Local account created. You are signed in.')
      setAuthMessageType('success')
    } else if (authMode === 'forgot') {
      if (!savedAccount) {
        setAuthMessage('That username was not found. Choose sign up to create a new account.')
        setAuthMessageType('error')
        return
      }
      if (trimmedPassword !== trimmedConfirmPassword) {
        setAuthMessage('New password and confirm password must match.')
        setAuthMessageType('error')
        return
      }
      const updatedAccounts = readStoredAccounts().map((account) =>
        account.username === trimmedUsername
          ? {
              ...account,
              password: trimmedPassword,
            }
          : account
      )
      writeStoredAccounts(updatedAccounts)
      setAuthMessage('Password reset. Sign in with your username and new password.')
      setAuthMessageType('success')
      setAuthMode('signin')
      setPasswordFormValue('')
      setConfirmPasswordFormValue('')
      return
    } else if (savedAccount) {
      if (savedAccount.password !== trimmedPassword) {
        setAuthMessage('That username or password does not match your saved local account.')
        setAuthMessageType('error')
        return
      }
      setAuthMessage('Signed in successfully.')
      setAuthMessageType('success')
    } else {
      setAuthMessage('That username was not found. Choose sign up to create a new account.')
      setAuthMessageType('error')
      return
    }

    const resolvedDisplayName = authMode === 'signup' ? trimmedName : savedAccount?.name || trimmedName
    setUserName(resolvedDisplayName)
    setCurrentUsername(trimmedUsername)
    setProfileNameDraft(resolvedDisplayName)
    setNameFormValue(resolvedDisplayName)
    setUsernameFormValue(trimmedUsername)
    setHasEnteredName(true)
    setPasswordFormValue('')
    setConfirmPasswordFormValue('')
    resetWorkspaceState()
    try {
      const raw = window.localStorage.getItem(getDraftStorageKey(trimmedUsername))
      if (raw) {
        applyWorkspaceDraft(JSON.parse(raw))
      }
    } catch {
      // Ignore malformed local storage.
    }
    const h = (window.location.hash || '').replace(/^#/, '')
    if (isValidTab(h)) {
      setActiveTab(h)
    }
  }

  const handleSaveProfileName = (event) => {
    event.preventDefault()
    const trimmedName = profileNameDraft.trim()
    if (!trimmedName) {
      setProfileSaveNotice('Name cannot be empty.')
      return
    }
    if (!currentUsername) {
      setProfileSaveNotice('No signed-in account was found to update.')
      return
    }

    const updatedAccounts = readStoredAccounts().map((account) =>
      account.username === currentUsername
        ? {
            ...account,
            name: trimmedName,
          }
        : account
    )
    writeStoredAccounts(updatedAccounts)
    setUserName(trimmedName)
    setNameFormValue(trimmedName)
    setProfileSaveNotice('Name updated.')
  }

  const goToTab = useCallback((tab) => {
    if (!isValidTab(tab)) {
      return
    }
    setActiveTab(tab)
  }, [])

  const handleStartNewInterviewSession = () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
    setIsRewriteSpeaking(false)
    setIsRewritePaused(false)
    setRewriteSpeechProgress(0)
    setInterviewError('')
    setLastScore(null)
    setLastFeedback('')
    setCurrentQuestion('')
    setCurrentAnswer('')
    setAnswerHistory([])
    setQuestionTrail([])
    setQuestionTrailIndex(0)
    setAnsweredCount(0)
    setTargetQuestionCount(0)
    setPendingNextQuestion('')
    setShowFollowUpPreview(false)
    setShowNextQuestionPreview(false)
    setWaitingForNextStep(false)
    setFinalEvaluation('')
    setInterviewComplete(false)
    setInterviewStatusMessage('')
    setInterviewStage('session')
    if (evaluationTimerRef.current) {
      window.clearTimeout(evaluationTimerRef.current)
      evaluationTimerRef.current = null
    }
    setInterviewViewActive(false)
    setLatestFollowUpQuestion('')
    setLatestCritique('')
    setLatestRewrite('')
    setDebriefActions([])
    setNextRoundTarget('')
    setCurriculumPlan([])
    setResumePromptAcknowledgedSessionId('')
    setInterviewHistoryPanelOpen(false)
    const id = createSessionId()
    setSessionId(id)
    try {
      window.localStorage.setItem(SESSION_ID_KEY, id)
    } catch {
      // Ignore.
    }
  }

  const handleContinueInterviewSession = async (targetSessionId = sessionId) => {
    if (!targetSessionId.trim()) {
      setInterviewError('Session ID is required to continue.')
      return
    }
    setInterviewError('')
    try {
      const response = await fetch(`${API_BASE_URL}/interview-sessions/${encodeURIComponent(targetSessionId)}`)
      if (!response.ok) {
        const message = await readErrorMessage(response, 'Failed to load interview session.')
        throw new Error(message)
      }
      const data = await response.json()
      const memory = data?.memory || {}
      const memoryHistory = Array.isArray(memory.history) ? memory.history : []
      const pending = memory.pending_next_step && typeof memory.pending_next_step === 'object' ? memory.pending_next_step : {}
      const lastAnswered = [...memoryHistory].reverse().find((item) => item && item.answer)
      const pendingItem = [...memoryHistory].reverse().find((item) => item && !item.answer)
      const questions = memoryHistory
        .map((item) => (typeof item?.question === 'string' ? item.question : ''))
        .filter(Boolean)
        .slice(-40)
      const mappedAnswerHistory = [...memoryHistory]
        .reverse()
        .filter((item) => item && item.answer)
        .map((item) => ({
          question: item.question || '',
          answer: item.answer || '',
          score: typeof item.score === 'number' ? item.score : null,
          feedback: item.feedback || '',
          rewrite: item.rewrite || '',
          answeredAt: item.answeredAt || '',
        }))
        .slice(0, 8)

      setSessionId(targetSessionId)
      setMode(memory.mode === 'technical' ? 'technical' : 'behavioral')
      setInterviewJobDescription(typeof memory.job_description === 'string' ? memory.job_description : '')
      setInterviewResume(typeof memory.resume === 'string' ? memory.resume : '')
      setPanelModeEnabled(Boolean(memory.panel_mode))
      setPressureRoundEnabled(Boolean(memory.pressure_round))
      setCompanyContext(typeof memory.company_context === 'string' ? memory.company_context : '')
      setRoleContext(typeof memory.role_context === 'string' ? memory.role_context : '')
      setInterviewDate(typeof memory.interview_date === 'string' ? memory.interview_date : '')
      setQuestionTrail(questions)
      setQuestionTrailIndex(Math.max(0, questions.length - 1))
      setCurrentQuestion(typeof pendingItem?.question === 'string' ? pendingItem.question : '')
      setCurrentAnswer('')
      setAnswerHistory(mappedAnswerHistory)
      setAnsweredCount(Number(memory.answered_count) || mappedAnswerHistory.length)
      setTargetQuestionCount(Number(memory.target_question_count) || 0)
      setInterviewComplete(Boolean(memory.interview_complete))
      setWaitingForNextStep(Boolean(pending.follow_up_question || pending.next_question))
      setLatestFollowUpQuestion(typeof pending.follow_up_question === 'string' ? pending.follow_up_question : '')
      setPendingNextQuestion(typeof pending.next_question === 'string' ? pending.next_question : '')
      setLastScore(typeof lastAnswered?.score === 'number' ? lastAnswered.score : null)
      setLastFeedback(typeof lastAnswered?.feedback === 'string' ? lastAnswered.feedback : '')
      setLatestCritique(typeof lastAnswered?.critique === 'string' ? lastAnswered.critique : '')
      setLatestRewrite(typeof lastAnswered?.rewrite === 'string' ? lastAnswered.rewrite : '')
      setFinalEvaluation(typeof memory.final_evaluation === 'string' ? memory.final_evaluation : '')
      setInterviewStage(Boolean(memory.interview_complete) ? 'completed' : 'session')
      setInterviewStatusMessage('Resumed from saved session.')
      setResumePromptAcknowledgedSessionId(targetSessionId)
      setInterviewHistoryPanelOpen(false)
      setInterviewViewActive(true)
      setActiveTab('interview')
      setAccountMenuOpen(false)
    } catch (error) {
      setInterviewError(error.message || 'Failed to load interview session.')
    }
  }

  const handlePauseInterviewToDashboard = () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
    setIsRewriteSpeaking(false)
    setIsRewritePaused(false)
    setInterviewViewActive(false)
    setInterviewHistoryPanelOpen(false)
    setInterviewStatusMessage('Session paused. You can continue this interview from the dashboard.')
    goToTab('resume')
  }

  const handleTailorResume = async (event) => {
    event.preventDefault()
    setResumeError('')
    setResumeSuccess('')
    setResumeCopyNotice('')
    setTailoredResumeData(null)

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
      const data = await response.json()
      setTailoredResumeData(data)
      setResumeSuccess('Tailored resume generated. You can copy and use it anywhere.')
      setPlanPhase('done')
    } catch (error) {
      setResumeError(error.message || 'Failed to tailor resume.')
      setPlanPhase('idle')
    } finally {
      setIsTailoring(false)
    }
  }

  const handleCopyTailoredResume = async () => {
    if (!tailoredResumeData) {
      return
    }
    const output = formatTailoredResumeForCopy(tailoredResumeData)
    if (!output) {
      return
    }
    try {
      await navigator.clipboard.writeText(output)
      setResumeCopyNotice('Tailored resume copied to clipboard.')
    } catch {
      setResumeCopyNotice('Copy failed — select the text and copy manually.')
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
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
    setIsRewriteSpeaking(false)
    setIsRewritePaused(false)
    setRewriteSpeechProgress(0)
    setInterviewError('')
    setLastScore(null)
    setLastFeedback('')
    setCurrentQuestion('')
    setCurrentAnswer('')
    setLatestFollowUpQuestion('')
    setLatestCritique('')
    setLatestRewrite('')
    setDebriefActions([])
    setNextRoundTarget('')
    setCurriculumPlan([])
    setPendingNextQuestion('')
    setShowFollowUpPreview(false)
    setShowNextQuestionPreview(false)
    setWaitingForNextStep(false)
    setAnsweredCount(0)
    setTargetQuestionCount(0)
    setFinalEvaluation('')
    setInterviewComplete(false)
    setQuestionTrail([])
    setQuestionTrailIndex(0)
    setInterviewStatusMessage('')
    setInterviewStage('session')
    if (evaluationTimerRef.current) {
      window.clearTimeout(evaluationTimerRef.current)
      evaluationTimerRef.current = null
    }

    if (!interviewJobDescription.trim() || !interviewResume.trim()) {
      setInterviewError('Mode, job description, and resume are required.')
      return
    }
    if (questionCountMode === 'custom') {
      const parsedCount = Number.parseInt(customQuestionCount, 10)
      if (!Number.isFinite(parsedCount) || parsedCount < 1 || parsedCount > 20) {
        setInterviewError('Choose a custom question count between 1 and 20.')
        return
      }
    }

    const hasInProgressSession = Boolean(
      currentQuestion || waitingForNextStep || (answeredCount > 0 && !interviewComplete)
    )
    const effectiveSessionId = hasInProgressSession ? sessionId.trim() : createSessionId()
    setSessionId(effectiveSessionId)
    try {
      window.localStorage.setItem(SESSION_ID_KEY, effectiveSessionId)
    } catch {
      // Ignore.
    }

    setIsStartingInterview(true)
    try {
      const requestPayload = {
        mode,
        session_id: effectiveSessionId,
        job_description: interviewJobDescription,
        resume: interviewResume,
        panel_mode: panelModeEnabled,
        pressure_round: pressureRoundEnabled,
        company_context: companyContext,
        role_context: roleContext,
        interview_date: interviewDate || null,
        target_question_count:
          questionCountMode === 'custom' ? Number.parseInt(customQuestionCount, 10) : undefined,
      }
      const response = await fetch(`${API_BASE_URL}/start-interview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestPayload),
      })

      if (!response.ok) {
        const message = await readErrorMessage(response, 'Failed to start interview.')
        throw new Error(message)
      }

      const data = await response.json()
      setCurrentQuestion(data.question || '')
      setQuestionTrail(data.question ? [data.question] : [])
      setQuestionTrailIndex(0)
      setInterviewViewActive(true)
      setInterviewStatusMessage(data.interview_started ? 'Interview started.' : '')
      setInterviewStage('session')
      setTargetQuestionCount(data.target_question_count || 0)
      setResumePromptAcknowledgedSessionId(effectiveSessionId)
      if (currentUsername) {
        setInterviewSessionsArchive((prev) => {
          const nextUpdatedAt = new Date().toISOString()
          const nextArchive = [...prev]
          const existingIndex = nextArchive.findIndex((session) => session.sessionId === effectiveSessionId)
          if (existingIndex >= 0) {
            const existing = nextArchive[existingIndex]
            nextArchive[existingIndex] = {
              ...existing,
              mode,
              startedAt: existing.startedAt || nextUpdatedAt,
              updatedAt: nextUpdatedAt,
              entries: Array.isArray(existing.entries) ? existing.entries : [],
            }
          } else {
            nextArchive.unshift({
              sessionId: effectiveSessionId,
              mode,
              startedAt: nextUpdatedAt,
              updatedAt: nextUpdatedAt,
              entries: [],
            })
          }
          nextArchive.sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)))
          writeInterviewArchive(currentUsername, nextArchive)
          return nextArchive
        })
      }
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
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel()
      }
      setIsRewriteSpeaking(false)
      setIsRewritePaused(false)
      setRewriteSpeechProgress(0)
      setLastScore(data.score ?? null)
      setLastFeedback(data.feedback ?? '')
      setLatestFollowUpQuestion(data.follow_up_question ?? '')
      setPendingNextQuestion(data.next_question ?? '')
      setShowFollowUpPreview(false)
      setShowNextQuestionPreview(false)
      setWaitingForNextStep(Boolean(data.waiting_for_next_step))
      setLatestCritique(data.critique ?? '')
      setLatestRewrite(data.rewrite ?? '')
      setDebriefActions(Array.isArray(data.debrief_actions) ? data.debrief_actions.slice(0, 3) : [])
      setNextRoundTarget(data.next_round_target ?? '')
      setCurriculumPlan(Array.isArray(data.curriculum_plan) ? data.curriculum_plan.slice(0, 7) : [])
      setFinalEvaluation(data.final_evaluation ?? '')
      const nextAnsweredCount = answeredCount + 1
      const derivedComplete =
        Boolean(data.interview_complete) ||
        (Number(targetQuestionCount) > 0 && nextAnsweredCount >= Number(targetQuestionCount))
      setInterviewComplete(derivedComplete)
      setAnsweredCount(nextAnsweredCount)
      const detectedWeakAreas = computeWeakAreas(currentAnswer, data.feedback ?? '', data.score ?? null)
      setWeakAreasMemory((prev) => [...detectedWeakAreas, ...prev].slice(0, 40))
      const historyEntry = {
        question: currentQuestion,
        answer: currentAnswer,
        score: data.score ?? null,
        feedback: data.feedback ?? '',
        rewrite: data.rewrite ?? '',
        answeredAt: new Date().toLocaleTimeString(),
      }
      setAnswerHistory((prev) => [historyEntry, ...prev])
      if (currentUsername) {
        setInterviewSessionsArchive((prev) => {
          const nextUpdatedAt = new Date().toISOString()
          const nextArchive = [...prev]
          const existingIndex = nextArchive.findIndex((session) => session.sessionId === sessionId)
          if (existingIndex >= 0) {
            const existing = nextArchive[existingIndex]
            nextArchive[existingIndex] = {
              ...existing,
              mode,
              startedAt: existing.startedAt || nextUpdatedAt,
              updatedAt: nextUpdatedAt,
              entries: [historyEntry, ...(Array.isArray(existing.entries) ? existing.entries : [])].slice(0, 80),
            }
          } else {
            nextArchive.unshift({
              sessionId,
              mode,
              startedAt: nextUpdatedAt,
              updatedAt: nextUpdatedAt,
              entries: [historyEntry],
            })
          }
          nextArchive.sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)))
          writeInterviewArchive(currentUsername, nextArchive)
          return nextArchive
        })
      }
      if (derivedComplete) {
        setCurrentQuestion('')
        setInterviewStatusMessage('Interview simulation done.')
        setInterviewStage('completed')
      } else {
        setInterviewStage('session')
        setInterviewStatusMessage('Choose your next step: follow-up question or next main question.')
      }
      // Keep the submitted answer visible while review feedback is shown.
    } catch (error) {
      setInterviewError(error.message || 'Failed to submit answer.')
    } finally {
      setIsSubmittingAnswer(false)
    }
  }

  const handleAdvanceInterview = async (choice) => {
    if (!waitingForNextStep || !sessionId.trim()) {
      return
    }
    setInterviewError('')
    setIsAdvancingInterview(true)
    try {
      const response = await fetch(`${API_BASE_URL}/advance-interview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          choice,
        }),
      })
      if (!response.ok) {
        const message = await readErrorMessage(response, 'Failed to advance interview.')
        throw new Error(message)
      }
      const data = await response.json()
      const nextQ = data.question || ''
      setCurrentQuestion(nextQ)
      if (nextQ) {
        setQuestionTrail((prev) => {
          const updated = [...prev, nextQ].slice(-40)
          setQuestionTrailIndex(Math.max(0, updated.length - 1))
          return updated
        })
      }
      setCurrentAnswer('')
      setWaitingForNextStep(false)
      setLatestFollowUpQuestion('')
      setPendingNextQuestion('')
      setShowFollowUpPreview(false)
      setShowNextQuestionPreview(false)
      setInterviewStatusMessage(choice === 'follow_up' ? 'Follow-up selected.' : 'Moved to next main question.')
    } catch (error) {
      setInterviewError(error.message || 'Failed to advance interview.')
    } finally {
      setIsAdvancingInterview(false)
    }
  }

  const startRewriteAudioFromProgress = useCallback(
    (progressValue) => {
      const speechSupported =
        typeof window !== 'undefined' &&
        'speechSynthesis' in window &&
        typeof window.SpeechSynthesisUtterance !== 'undefined'
      if (!latestRewrite.trim() || !speechSupported || typeof window === 'undefined') {
        return
      }
      const fullText = latestRewrite.trim()
      const clampedProgress = Math.max(0, Math.min(100, progressValue))
      const rawStartIndex = Math.floor((clampedProgress / 100) * fullText.length)
      const boundedStart = Math.max(0, Math.min(fullText.length - 1, rawStartIndex))
      const rawSlice = fullText.slice(boundedStart)
      const spokenSlice = rawSlice.trimStart()
      if (!spokenSlice) {
        setRewriteSpeechProgress(100)
        setIsRewriteSpeaking(false)
        setIsRewritePaused(false)
        return
      }
      const leadingTrimCount = rawSlice.length - spokenSlice.length
      rewriteSpeechOffsetRef.current = boundedStart + leadingTrimCount
      window.speechSynthesis.cancel()
      const utterance = new window.SpeechSynthesisUtterance(spokenSlice)
      utterance.rate = 1
      utterance.pitch = 1
      utterance.onboundary = (event) => {
        if (typeof event.charIndex !== 'number' || !fullText.length) {
          return
        }
        const absoluteChar = rewriteSpeechOffsetRef.current + event.charIndex
        const nextProgress = Math.max(0, Math.min(100, (absoluteChar / fullText.length) * 100))
        setRewriteSpeechProgress(nextProgress)
      }
      utterance.onend = () => {
        setIsRewriteSpeaking(false)
        setIsRewritePaused(false)
        setRewriteSpeechProgress(100)
      }
      utterance.onerror = () => {
        setIsRewriteSpeaking(false)
        setIsRewritePaused(false)
      }
      rewriteUtteranceRef.current = utterance
      window.speechSynthesis.speak(utterance)
      setIsRewriteSpeaking(true)
      setIsRewritePaused(false)
    },
    [latestRewrite]
  )

  const handleRewritePlayAudio = () => {
    const speechSupported =
      typeof window !== 'undefined' &&
      'speechSynthesis' in window &&
      typeof window.SpeechSynthesisUtterance !== 'undefined'
    if (!latestRewrite.trim() || !speechSupported || typeof window === 'undefined') {
      return
    }
    if (isRewriteSpeaking && isRewritePaused) {
      window.speechSynthesis.resume()
      setIsRewritePaused(false)
      return
    }
    if (!isRewriteSpeaking) {
      const startAt = rewriteSpeechProgress >= 99 ? 0 : rewriteSpeechProgress
      startRewriteAudioFromProgress(startAt)
    }
  }

  const handleRewritePauseAudio = () => {
    const speechSupported =
      typeof window !== 'undefined' &&
      'speechSynthesis' in window &&
      typeof window.SpeechSynthesisUtterance !== 'undefined'
    if (!latestRewrite.trim() || !speechSupported || typeof window === 'undefined') {
      return
    }
    if (!isRewriteSpeaking || isRewritePaused) {
      return
    }
    window.speechSynthesis.pause()
    setIsRewritePaused(true)
  }

  const handleRewriteRestartAudio = () => {
    const speechSupported =
      typeof window !== 'undefined' &&
      'speechSynthesis' in window &&
      typeof window.SpeechSynthesisUtterance !== 'undefined'
    if (!latestRewrite.trim() || !speechSupported || typeof window === 'undefined') {
      return
    }
    setRewriteSpeechProgress(0)
    startRewriteAudioFromProgress(0)
  }

  const handleRewriteSeekChange = (event) => {
    setRewriteSpeechProgress(Number(event.target.value))
  }

  const handleRewriteSeekCommit = () => {
    const speechSupported =
      typeof window !== 'undefined' &&
      'speechSynthesis' in window &&
      typeof window.SpeechSynthesisUtterance !== 'undefined'
    if (!speechSupported || typeof window === 'undefined' || !latestRewrite.trim()) {
      return
    }
    startRewriteAudioFromProgress(rewriteSpeechProgress)
  }

  const handleViewEvaluationResults = () => {
    setInterviewStage('preparing')
    setInterviewStatusMessage('Evaluating your results...')
    if (evaluationTimerRef.current) {
      window.clearTimeout(evaluationTimerRef.current)
    }
    evaluationTimerRef.current = window.setTimeout(() => {
      setInterviewStage('results')
      setInterviewStatusMessage('Your interview evaluation is ready.')
      evaluationTimerRef.current = null
    }, 1800)
  }

  if (!hasEnteredName) {
    return (
      <div className="welcome-page">
        <div className="welcome-orb welcome-orb--left" aria-hidden="true" />
        <div className="welcome-orb welcome-orb--right" aria-hidden="true" />
        <div className="welcome-grid">
          <section className="welcome-hero">
            <p className="welcome-eyebrow">Agentic Interview Helper</p>
            <h1>Prepare with clarity. Answer with confidence.</h1>
            <p className="welcome-copy">
              Practice sharper answers, hear them back naturally, and step into your interview with a calmer, more
              polished story.
            </p>
            <div className="welcome-feature-row" aria-label="Product highlights">
              <div className="welcome-feature-card">
                <span className="welcome-feature-card__label">Adaptive practice</span>
                <strong>Real-time follow-ups</strong>
                <p>Get dynamic mock questions that react to your answer quality and weak spots.</p>
              </div>
              <div className="welcome-feature-card">
                <span className="welcome-feature-card__label">Answer coaching</span>
                <strong>Rewrite and listen</strong>
                <p>Turn rough drafts into stronger interview responses and hear them in a cleaner cadence.</p>
              </div>
            </div>
          </section>

          <section className="welcome-card">
            <div className="welcome-card__top">
              <p className="welcome-card__eyebrow">Open your workspace</p>
            </div>
            <h2>Lets begin!</h2>
            <p className="welcome-card__copy">
              {authMode === 'signup'
                ? 'Create your local account with a first name and a unique username so the dashboard can greet you personally.'
                : authMode === 'forgot'
                  ? 'Reset your local password with your saved username.'
                  : 'Sign in with your username and password to open your interview prep dashboard.'}
            </p>
            <div className="welcome-auth-switch" role="tablist" aria-label="Authentication mode">
              <button
                type="button"
                className={authMode === 'signin' ? 'welcome-auth-switch__item welcome-auth-switch__item--active' : 'welcome-auth-switch__item'}
                onClick={() => {
                  setAuthMode('signin')
                  setAuthMessage('')
                  setConfirmPasswordFormValue('')
                }}
              >
                Sign in
              </button>
              <button
                type="button"
                className={authMode === 'signup' ? 'welcome-auth-switch__item welcome-auth-switch__item--active' : 'welcome-auth-switch__item'}
                onClick={() => {
                  setAuthMode('signup')
                  setAuthMessage('')
                }}
              >
                Sign up
              </button>
            </div>
            <form onSubmit={handleEnterApp} className="form">
              {authMode === 'signup' ? (
                <label>
                  First Name
                  <input
                    type="text"
                    value={nameFormValue}
                    onChange={(event) => {
                      setNameFormValue(event.target.value)
                      setAuthMessage('')
                    }}
                    placeholder="Enter your first name"
                    required
                    maxLength={40}
                    autoFocus
                    autoComplete="name"
                  />
                </label>
              ) : null}
              <label>
                Username
                <input
                  type="text"
                  value={usernameFormValue}
                  onChange={(event) => {
                    setUsernameFormValue(event.target.value)
                    setAuthMessage('')
                  }}
                  placeholder="Choose a username"
                  required
                  autoFocus={authMode !== 'signup'}
                  autoComplete="username"
                  spellCheck={false}
                />
              </label>
              <label>
                {authMode === 'forgot' ? 'New Password' : 'Password'}
                <input
                  type="password"
                  value={passwordFormValue}
                  onChange={(event) => {
                    setPasswordFormValue(event.target.value)
                    setAuthMessage('')
                  }}
                  placeholder={authMode === 'forgot' ? 'Enter your new password' : 'Enter your password'}
                  required
                  autoComplete={authMode === 'signin' ? 'current-password' : 'new-password'}
                />
              </label>
              {authMode === 'signup' || authMode === 'forgot' ? (
                <label>
                  Confirm Password
                  <input
                    type="password"
                    value={confirmPasswordFormValue}
                    onChange={(event) => {
                      setConfirmPasswordFormValue(event.target.value)
                      setAuthMessage('')
                    }}
                    placeholder="Confirm your password"
                    required
                    autoComplete="new-password"
                  />
                </label>
              ) : null}
              <p className="welcome-hint">
                Your local account is saved in this browser. Passwords must be at least 8 characters and include
                lowercase, uppercase, and a number. Special characters are allowed. Usernames must be unique. Use links like
                <code>#interview</code> or <code>#outreach</code> to jump straight into a tab later.
              </p>
              {authMode === 'signin' ? (
                <button
                  type="button"
                  className="welcome-link-button"
                  onClick={() => {
                    setAuthMode('forgot')
                    setAuthMessage('')
                    setPasswordFormValue('')
                    setConfirmPasswordFormValue('')
                  }}
                >
                  Forgot password?
                </button>
              ) : null}
              {authMessage ? (
                <p
                  className={
                    authMessageType === 'error'
                      ? 'message message--error welcome-auth-message'
                      : authMessageType === 'success'
                        ? 'message message--success welcome-auth-message'
                        : 'message message--info welcome-auth-message'
                  }
                >
                  {authMessage}
                </p>
              ) : null}
              <button type="submit" className="welcome-submit">
                {authMode === 'signup'
                  ? 'Create account'
                  : authMode === 'forgot'
                    ? 'Reset password'
                    : "Let's get started"}
              </button>
            </form>
          </section>
        </div>
      </div>
    )
  }

  if (interviewViewActive) {
    return (
      <div className="workspace">
        <header className="workspace-topbar">
          <div className="workspace-topbar__brand">
            <span className="workspace-topbar__mark" aria-hidden="true">
              AI
            </span>
            <div className="workspace-topbar__brand-text">
              <span className="workspace-topbar__name">Interview Room</span>
              <span className="workspace-topbar__tagline">Focused mock interview session</span>
            </div>
          </div>
          <div className="workspace-topbar__actions">
            <button
              type="button"
              className="button button--topbar-ghost interview-history-toggle"
              onClick={() => setInterviewHistoryPanelOpen((open) => !open)}
              aria-expanded={interviewHistoryPanelOpen}
              aria-controls="interview-history-panel"
              aria-label="Open interview history panel"
            >
              <span aria-hidden="true">☰</span>
            </button>
            <button
              type="button"
              className="button button--secondary"
              onClick={handlePauseInterviewToDashboard}
            >
              Pause & go to dashboard
            </button>
          </div>
        </header>
        <main className="workspace-main" tabIndex={-1}>
          <div className="workspace-inner">
            {interviewHistoryPanelOpen ? (
              <aside id="interview-history-panel" className="question-card interview-history-panel">
                <h3>Session Transcript</h3>
                {interviewTranscriptItems.length > 0 ? (
                  <ul className="history-list">
                    {interviewTranscriptItems.map((item, index) => (
                      <li key={`${item.question}-${index}`}>
                        <p>
                          <strong>Question:</strong> {item.question || 'No question captured.'}
                        </p>
                        <p>
                          <strong>Your answer:</strong> {item.answer || 'Not answered yet.'}
                        </p>
                        <p>
                          <strong>Agent answer:</strong> {item.agentAnswer || 'No suggested answer yet.'}
                        </p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">No transcript entries yet.</p>
                )}
              </aside>
            ) : null}
            <section className="panel workspace-panel">
              <h2>Live Interview</h2>
              <div className="interview-meta-row">
                {interviewStatusMessage && interviewStage !== 'results' && interviewStage !== 'completed' ? (
                  <span className="interview-status-chip">{interviewStatusMessage}</span>
                ) : null}
                <p className="field-hint interview-progress-hint">
                  Progress: {answeredCount}/{targetQuestionCount || '?'} answered
                </p>
              </div>
              {interviewStage === 'preparing' ? (
                <div className="evaluation-preparing">
                  <h3>Evaluating Your Interview...</h3>
                  <p>Analyzing your answers, strengths, and key improvement opportunities.</p>
                  <div className="evaluation-preparing__dots" aria-hidden="true">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              ) : null}
              {interviewStage === 'completed' ? (
                <div className="evaluation-results">
                  <h3>Interview Simulation Done</h3>
                  <p className="evaluation-results__lede">
                    Nice work finishing your interview simulation. Your responses are saved and ready for evaluation.
                  </p>
                  <article className="evaluation-results__card">
                    <h4>Session Summary</h4>
                    <p>
                      You answered {answeredCount} of {targetQuestionCount || answeredCount} planned questions.
                    </p>
                  </article>
                  <div className="row">
                    <button type="button" className="button button--primary" onClick={handleViewEvaluationResults}>
                      View evaluated results
                    </button>
                    <button type="button" className="button button--secondary" onClick={handleStartNewInterviewSession}>
                      Start new interview
                    </button>
                  </div>
                </div>
              ) : null}
              {interviewStage === 'results' ? (
                <div className="evaluation-results">
                  <h3>Interview Completed</h3>
                  <p className="evaluation-results__lede">
                    Great work completing your mock interview. Here is your personalized evaluation and next-step plan.
                  </p>
                  {finalEvaluation ? (
                    <article className="evaluation-results__card">
                      <h4>Overall Evaluation</h4>
                      <p>{finalEvaluation}</p>
                    </article>
                  ) : null}
                  {debriefActions.length > 0 ? (
                    <article className="evaluation-results__card">
                      <h4>Action Plan</h4>
                      <ul className="history-list">
                        {debriefActions.map((action) => (
                          <li key={action}>{action}</li>
                        ))}
                      </ul>
                    </article>
                  ) : null}
                  {nextRoundTarget ? (
                    <article className="evaluation-results__card">
                      <h4>Next Interview Target</h4>
                      <p>{nextRoundTarget}</p>
                    </article>
                  ) : null}
                  {curriculumPlan.length > 0 ? (
                    <article className="evaluation-results__card">
                      <h4>Preparation Curriculum</h4>
                      <ul className="history-list">
                        {curriculumPlan.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </article>
                  ) : null}
                  <div className="row">
                    <button type="button" className="button button--primary" onClick={handleStartNewInterviewSession}>
                      Start new interview
                    </button>
                    <button
                      type="button"
                      className="button button--secondary"
                      onClick={() => {
                        setInterviewViewActive(false)
                        goToTab('interview')
                      }}
                    >
                      Back to dashboard
                    </button>
                  </div>
                </div>
              ) : null}
              {interviewStage === 'session' ? (
                <>
              {questionTrail.length > 1 ? (
                <div className="row">
                  <button
                    type="button"
                    className="button button--secondary"
                    disabled={questionTrailIndex <= 0}
                    onClick={() => setQuestionTrailIndex((prev) => Math.max(0, prev - 1))}
                  >
                    Previous question
                  </button>
                </div>
              ) : null}
              {displayedQuestion ? (
                <div className="question-card">
                  <h3>{isViewingLatestQuestion ? 'Current Question' : 'Previous Question (read-only view)'}</h3>
                  <p>{displayedQuestion}</p>
                </div>
              ) : null}

              {!interviewComplete && currentQuestion ? (
                <form onSubmit={handleSubmitAnswer} className="form">
                  <label>
                    Your Answer
                    <textarea
                      value={currentAnswer}
                      onChange={(event) => setCurrentAnswer(event.target.value)}
                      rows={7}
                      placeholder="Write your interview answer..."
                      required
                      disabled={!isViewingLatestQuestion || waitingForNextStep}
                    />
                  </label>
                  <button
                    type="submit"
                    disabled={isSubmittingAnswer || waitingForNextStep || !isViewingLatestQuestion}
                  >
                    {isSubmittingAnswer ? 'Submitting...' : 'Submit Answer'}
                  </button>
                </form>
              ) : null}

              {waitingForNextStep ? (
                <div className="question-card next-step-card">
                  <h3>Choose next step</h3>
                  <p className="next-step-card__subtitle">
                    Pick one path. You can preview each question before choosing.
                  </p>
                  <div className="next-step-grid">
                    <article className="next-step-option">
                      <h4>Follow-up path</h4>
                      <button
                        type="button"
                        className="button button--ghost"
                        disabled={!latestFollowUpQuestion}
                        onClick={() => setShowFollowUpPreview((prev) => !prev)}
                      >
                        {showFollowUpPreview ? 'Hide preview' : 'Preview question'}
                      </button>
                      {latestFollowUpQuestion && showFollowUpPreview ? (
                        <p className="message message--info">
                          {latestFollowUpQuestion}
                        </p>
                      ) : null}
                      <button
                        type="button"
                        className="button button--primary"
                        disabled={!latestFollowUpQuestion || isAdvancingInterview}
                        onClick={() => void handleAdvanceInterview('follow_up')}
                      >
                        {isAdvancingInterview ? 'Loading...' : 'Answer follow-up'}
                      </button>
                    </article>

                    <article className="next-step-option">
                      <h4>Next main question</h4>
                      <button
                        type="button"
                        className="button button--ghost"
                        disabled={!pendingNextQuestion}
                        onClick={() => setShowNextQuestionPreview((prev) => !prev)}
                      >
                        {showNextQuestionPreview ? 'Hide preview' : 'Preview question'}
                      </button>
                      {pendingNextQuestion && showNextQuestionPreview ? (
                        <p className="message message--info">
                          {pendingNextQuestion}
                        </p>
                      ) : null}
                      <button
                        type="button"
                        className="button button--secondary"
                        disabled={!pendingNextQuestion || isAdvancingInterview}
                        onClick={() => void handleAdvanceInterview('next_question')}
                      >
                        Go to next question
                      </button>
                    </article>
                  </div>
                </div>
              ) : null}

              {activeTab === 'interview' && lastScore !== null ? (
                <p className="message message--info">Score: {lastScore} / 10</p>
              ) : null}
              {lastFeedback ? <p className="message message--success">{lastFeedback}</p> : null}
              {latestCritique ? (
                <p className="message message--info">
                  <strong>Critique:</strong> {latestCritique}
                </p>
              ) : null}
              {latestRewrite ? (
                <div className="message message--success">
                  <p>
                    <strong>Suggested rewrite:</strong> {latestRewrite}
                  </p>
                  <div className="rewrite-audio-row">
                    <div className="rewrite-audio-controls">
                      <button
                        type="button"
                        className="button button--ghost rewrite-audio-icon-btn"
                        disabled={!speechSupported}
                        onClick={handleRewritePlayAudio}
                        aria-label="Play audio"
                      >
                        <span aria-hidden="true">{'>'}</span>
                      </button>
                      <button
                        type="button"
                        className="button button--ghost rewrite-audio-icon-btn"
                        disabled={!speechSupported}
                        onClick={handleRewritePauseAudio}
                        aria-label="Pause audio"
                      >
                        <span aria-hidden="true">||</span>
                      </button>
                      <button
                        type="button"
                        className="button button--ghost rewrite-audio-icon-btn"
                        disabled={!speechSupported}
                        onClick={handleRewriteRestartAudio}
                        aria-label="Restart audio from beginning"
                      >
                        <span aria-hidden="true">🔊</span>
                      </button>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        step="1"
                        value={Math.round(rewriteSpeechProgress)}
                        onChange={handleRewriteSeekChange}
                        onMouseUp={handleRewriteSeekCommit}
                        onTouchEnd={handleRewriteSeekCommit}
                        className="rewrite-audio-slider"
                        aria-label="Rewrite audio position"
                        disabled={!speechSupported}
                      />
                    </div>
                  </div>
                </div>
              ) : null}
                </>
              ) : null}

              {interviewError ? <p className="message message--error">{interviewError}</p> : null}
            </section>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="workspace">
      <a href="#workspace-content" className="skip-link">
        Skip to main content
      </a>
      <header className="workspace-topbar">
        <div className="workspace-topbar__brand">
          <span className="workspace-topbar__mark" aria-hidden="true">
            AI
          </span>
          <div className="workspace-topbar__brand-text">
            <span className="workspace-topbar__name">Agentic Interview Helper</span>
            <span className="workspace-topbar__tagline">Agentic interview prep</span>
          </div>
        </div>
        <div className="workspace-topbar__actions">
          <span className="workspace-topbar__user">{userName}</span>
          <div className="account-menu">
            <button
              type="button"
              className="button button--topbar-ghost"
              onClick={() => {
                setAccountMenuOpen((open) => !open)
                setProfileNameDraft(userName)
                setProfileSaveNotice('')
              }}
              aria-expanded={accountMenuOpen}
              aria-controls="account-menu-panel"
            >
              Account
            </button>
            {accountMenuOpen ? (
              <div id="account-menu-panel" className="account-menu__panel">
                <form onSubmit={handleSaveProfileName} className="form account-menu__form">
                  <label>
                    Change display name
                    <input
                      type="text"
                      value={profileNameDraft}
                      onChange={(event) => {
                        setProfileNameDraft(event.target.value)
                        setProfileSaveNotice('')
                      }}
                      placeholder="Update your name"
                      required
                      autoComplete="name"
                    />
                  </label>
                  {profileSaveNotice ? <p className="account-menu__notice">{profileSaveNotice}</p> : null}
                  <div className="account-menu__actions">
                    <button type="submit" className="button button--secondary">
                      Save name
                    </button>
                    <button
                      type="button"
                      className="button button--ghost"
                      onClick={() => {
                        setHasEnteredName(false)
                        setCurrentUsername('')
                        setAccountMenuOpen(false)
                        setAuthMode('signin')
                        resetWorkspaceState()
                        setPasswordFormValue('')
                        setConfirmPasswordFormValue('')
                        setAuthMessage('Signed out. Enter your username and password to sign back in.')
                        setAuthMessageType('info')
                      }}
                    >
                      Sign out
                    </button>
                  </div>
                </form>
                <div className="account-menu__sessions">
                  <p className="account-menu__sessions-title">Interview sessions</p>
                  {interviewSessionsArchive.length > 0 ? (
                    <ul className="account-menu__session-list">
                      {interviewSessionsArchive.map((session) => (
                        <li key={session.sessionId} className="account-menu__session-item">
                          <details>
                            <summary>
                              <span>{session.sessionId}</span>
                              <span className="muted">
                                {session.startedAt ? `Started ${formatDateTime(session.startedAt)} · ` : ''}
                                {session.mode} · {session.entries.length} answer
                                {session.entries.length === 1 ? '' : 's'}
                              </span>
                            </summary>
                            {session.entries.length > 0 ? (
                              <ul className="account-menu__entry-list">
                                {session.entries.map((entry, index) => (
                                  <li key={`${session.sessionId}-${index}`} className="account-menu__entry-item">
                                    <p>
                                      <strong>Q:</strong> {entry.question || 'No question captured.'}
                                    </p>
                                    <p>
                                      <strong>Your answer:</strong> {entry.answer || 'No answer captured.'}
                                    </p>
                                    <p>
                                      <strong>Suggested answer:</strong>{' '}
                                      {entry.rewrite || 'No rewrite suggestion returned.'}
                                    </p>
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="account-menu__notice">No answered questions captured for this session yet.</p>
                            )}
                          </details>
                          <button
                            type="button"
                            className="button button--ghost"
                            onClick={() => void handleContinueInterviewSession(session.sessionId)}
                          >
                            Open session
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="account-menu__notice">No saved interview sessions yet. Submit an answer to start history.</p>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </header>
      <div className="workspace-accent" aria-hidden="true" />
      <main id="workspace-content" className="workspace-main" tabIndex={-1}>
        <div className="workspace-inner">
          <section className="workspace-intro" aria-label="Overview">
            <h1 className="workspace-intro__title">{friendlyGreeting}</h1>
            <p className="workspace-intro__lede">{friendlyFact}</p>
            <p className="workspace-api">
              API <code>{API_BASE_URL}</code>
              {apiHealth === 'checking' ? (
                <span className="api-health api-health--checking" aria-live="polite">
                  Checking…
                </span>
              ) : apiHealth === 'ok' ? (
                <span className="api-health api-health--ok" aria-live="polite">
                  Connected
                </span>
              ) : (
                <span className="api-health api-health--err" role="status">
                  Backend unreachable — start the API for resume, interview, and live outreach.
                </span>
              )}
            </p>
          </section>

          <section className="workflow-strip panel workspace-panel" aria-label="Workflow assistant">
            <div className="workflow-strip__row">
              <p className="workflow-strip__item">
                <span className="workflow-strip__label">Progress</span>
                <strong>
                  {completedActivitySteps}/{activitySteps.length}
                </strong>
              </p>
              <p className="workflow-strip__item">
                <span className="workflow-strip__label">Next</span>
                <span>{nextStepLabel}</span>
              </p>
              <p className="workflow-strip__item">
                <span className="workflow-strip__label">Insight</span>
                <span>{topInsights[0] || 'Add more context to unlock guidance.'}</span>
              </p>
              <p className="workflow-strip__item workflow-strip__status">
                <span className="workflow-strip__label">Agent Status</span>
                <span>
                  {agentLiveStatus.isRunning ? <span className="workflow-strip__pulse" aria-hidden="true" /> : null}
                  {agentLiveStatus.text}
                </span>
              </p>
              {activeTab === 'interview' ? (
                <p className="workflow-strip__item">
                  <span className="workflow-strip__label">Readiness</span>
                  <strong>{readinessScore}%</strong>
                </p>
              ) : null}
            </div>
            <details className="workflow-strip__details">
              <summary>More details</summary>
              <div className="workflow-strip__details-grid">
                <div>
                  <h3>Workflow Timeline</h3>
                  <ul className="step-list">
                    {planSteps.map((step) => (
                      <li key={step.key} className={`step step--${step.status}`}>
                        <span className="step__dot" />
                        <span>{step.label}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3>Confidence</h3>
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
                  <h3>Recent Agent Actions</h3>
                  <ul className="insight-list">
                    {recentAgentActions.map((action) => (
                      <li key={action}>{action}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </details>
          </section>

          <nav
            className="tabs tabs--workspace"
            role="tablist"
            aria-label="Feature sections"
          >
        <button
          type="button"
          className={activeTab === 'resume' ? 'tab tab--active' : 'tab'}
          role="tab"
          id="tab-resume"
          aria-selected={activeTab === 'resume'}
          aria-controls="panel-resume"
          onClick={() => goToTab('resume')}
        >
          Tailor Resume
        </button>
        <button
          type="button"
          className={activeTab === 'interview' ? 'tab tab--active' : 'tab'}
          role="tab"
          id="tab-interview"
          aria-selected={activeTab === 'interview'}
          aria-controls="panel-interview"
          onClick={() => goToTab('interview')}
        >
          Interview Simulator
        </button>
        <button
          type="button"
          className={activeTab === 'outreach' ? 'tab tab--active' : 'tab'}
          role="tab"
          id="tab-outreach"
          aria-selected={activeTab === 'outreach'}
          aria-controls="panel-outreach"
          onClick={() => goToTab('outreach')}
        >
          Professional outreach
        </button>
      </nav>

              {activeTab === 'resume' ? (
        <section
          className="panel workspace-panel"
          id="panel-resume"
          role="tabpanel"
          aria-labelledby="tab-resume"
        >
          <h2>Generate Tailored Resume</h2>
          <form onSubmit={handleTailorResume} className="form">
            <label>
              Resume Text
              <textarea
                value={resumeText}
                onChange={(event) => setResumeText(event.target.value)}
                rows={10}
                placeholder="Paste your current resume text..."
                required
                aria-describedby="hint-resume-wc"
              />
              <span id="hint-resume-wc" className="field-hint">
                {resumeWordCount} word{resumeWordCount === 1 ? '' : 's'}
              </span>
            </label>

            <label>
              Job Description
              <textarea
                value={jobDescription}
                onChange={(event) => setJobDescription(event.target.value)}
                rows={10}
                placeholder="Paste the target job description..."
                required
                aria-describedby="hint-jd-wc"
              />
              <span id="hint-jd-wc" className="field-hint">
                {jdWordCount} word{jdWordCount === 1 ? '' : 's'}
              </span>
            </label>

            <button type="submit" className="button button--secondary" disabled={isTailoring}>
              {isTailoring ? 'Generating...' : 'Tailor Resume'}
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

          {tailoredResumeData ? (
            <div className="question-card">
              <h3>Tailored Resume Output</h3>
              <div className="button-row">
                <button type="button" className="button button--secondary" onClick={handleCopyTailoredResume}>
                  Copy tailored resume
                </button>
              </div>
              {resumeCopyNotice ? <p className="message message--info">{resumeCopyNotice}</p> : null}

              {tailoredResumeData.summary ? (
                <>
                  <h4>Summary</h4>
                  <p>{tailoredResumeData.summary}</p>
                </>
              ) : null}

              {Array.isArray(tailoredResumeData.experience) && tailoredResumeData.experience.length > 0 ? (
                <>
                  <h4>Experience</h4>
                  <ul className="history-list">
                    {tailoredResumeData.experience.map((item, index) => (
                      <li key={`${item.company || 'experience'}-${index}`}>
                        <p>
                          <strong>{item.title || 'Role'}</strong>
                          {item.company ? ` - ${item.company}` : ''}
                        </p>
                        {Array.isArray(item.points) && item.points.length > 0 ? (
                          <ul className="history-list">
                            {item.points.map((point, pointIndex) => (
                              <li key={`${point}-${pointIndex}`}>{point}</li>
                            ))}
                          </ul>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </>
              ) : null}

              {Array.isArray(tailoredResumeData.skills) && tailoredResumeData.skills.length > 0 ? (
                <>
                  <h4>Skills</h4>
                  <p>{tailoredResumeData.skills.join(', ')}</p>
                </>
              ) : null}
            </div>
          ) : null}
        </section>
          ) : activeTab === 'interview' ? (
        <section
          className="panel workspace-panel"
          id="panel-interview"
          role="tabpanel"
          aria-labelledby="tab-interview"
        >
          <h2>Adaptive Interview Session</h2>
          {shouldPromptToResumeInterview ? (
            <div className="message message--info interview-resume-prompt">
              <p>
                <strong>Continue previous session?</strong>{' '}
                {currentSessionArchiveEntry?.startedAt
                  ? `This interview started on ${formatDateTime(currentSessionArchiveEntry.startedAt)}.`
                  : 'We found an in-progress interview session.'}
              </p>
              <div className="account-menu__actions">
                <button
                  type="button"
                  className="button button--secondary"
                  onClick={() => void handleContinueInterviewSession(sessionId)}
                >
                  Continue session
                </button>
                <button type="button" className="button button--ghost" onClick={handleStartNewInterviewSession}>
                  Start new interview
                </button>
              </div>
            </div>
          ) : null}
          <form onSubmit={handleStartInterview} className="form">
            <div className="row">
              <label>
                Interview Mode
                <select value={mode} onChange={(event) => setMode(event.target.value)} required>
                  <option value="behavioral">Behavioral</option>
                  <option value="technical">Technical</option>
                </select>
              </label>

              <div className="field-with-action">
                <label className="field-with-action__label">
                  Session ID
                  <input
                    type="text"
                    value={sessionId}
                    onChange={(event) => setSessionId(event.target.value)}
                    placeholder="Auto-generated; edit if you share across devices"
                    required
                    autoComplete="off"
                    spellCheck={false}
                  />
                </label>
                <button
                  className="button button--secondary"
                  type="button"
                  onClick={handleStartNewInterviewSession}
                >
                  New session
                </button>
              </div>
            </div>
            <div className="row">
              <label>
                <input
                  type="checkbox"
                  checked={panelModeEnabled}
                  onChange={(event) => setPanelModeEnabled(event.target.checked)}
                />{' '}
                <span className="interview-toggle-label">
                  Enable panel simulation mode
                  <span className="help-tooltip">
                    <button
                      type="button"
                      className="help-tooltip__trigger"
                      aria-label="What is panel simulation mode?"
                    >
                      ?
                    </button>
                    <span className="help-tooltip__content" role="tooltip">
                      Simulates multiple interviewers so follow-up questions can shift perspective like a real panel.
                    </span>
                  </span>
                </span>
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={pressureRoundEnabled}
                  onChange={(event) => setPressureRoundEnabled(event.target.checked)}
                />{' '}
                <span className="interview-toggle-label">
                  Enable pressure round style
                  <span className="help-tooltip">
                    <button
                      type="button"
                      className="help-tooltip__trigger"
                      aria-label="What is pressure round style?"
                    >
                      ?
                    </button>
                    <span className="help-tooltip__content" role="tooltip">
                      Increases challenge with tighter, more direct prompts to practice calm and concise responses.
                    </span>
                  </span>
                </span>
              </label>
            </div>
            <fieldset className="question-count-chooser">
              <legend>Interview length</legend>
              <label className="question-count-chooser__option">
                <input
                  type="radio"
                  name="question-count-mode"
                  value="agent"
                  checked={questionCountMode === 'agent'}
                  onChange={() => setQuestionCountMode('agent')}
                />
                <span>Use agent recommendation based on the role</span>
              </label>
              <label className="question-count-chooser__option">
                <input
                  type="radio"
                  name="question-count-mode"
                  value="custom"
                  checked={questionCountMode === 'custom'}
                  onChange={() => setQuestionCountMode('custom')}
                />
                <span>Let me choose how many questions to answer</span>
              </label>
              {questionCountMode === 'custom' ? (
                <label className="question-count-chooser__input">
                  Number of questions
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={customQuestionCount}
                    onChange={(event) => setCustomQuestionCount(event.target.value)}
                  />
                </label>
              ) : null}
            </fieldset>
            <p className="field-hint field-hint--block">
              Same ID keeps the backend interview memory. Use a new one to start a fresh run (clears the current
              question and your saved answers in this view).
            </p>
            <div className="row">
              <label>
                Company Context (optional)
                <input
                  type="text"
                  value={companyContext}
                  onChange={(event) => setCompanyContext(event.target.value)}
                  placeholder="e.g. B2B SaaS, strict SLAs, distributed team"
                />
              </label>
              <label>
                Role Context (optional)
                <input
                  type="text"
                  value={roleContext}
                  onChange={(event) => setRoleContext(event.target.value)}
                  placeholder="e.g. Senior backend, platform reliability"
                />
              </label>
            </div>
            <label>
              Interview Date (optional, for adaptive curriculum)
              <input
                type="date"
                value={interviewDate}
                onChange={(event) => setInterviewDate(event.target.value)}
              />
            </label>

            <label>
              Job Description
              <textarea
                value={interviewJobDescription}
                onChange={(event) => setInterviewJobDescription(event.target.value)}
                rows={8}
                placeholder="Paste the target job description..."
                required
                aria-describedby="hint-iv-jd-wc"
              />
              <span id="hint-iv-jd-wc" className="field-hint">
                {interviewJdWordCount} word{interviewJdWordCount === 1 ? '' : 's'}
              </span>
            </label>

            <label>
              Resume Text
              <textarea
                value={interviewResume}
                onChange={(event) => setInterviewResume(event.target.value)}
                rows={8}
                placeholder="Paste your resume text..."
                required
                aria-describedby="hint-iv-r-wc"
              />
              <span id="hint-iv-r-wc" className="field-hint">
                {interviewResumeWordCount} word{interviewResumeWordCount === 1 ? '' : 's'}
              </span>
            </label>

            <button type="submit" className="button button--secondary" disabled={isStartingInterview}>
              {isStartingInterview ? 'Starting Interview...' : 'Start Interview'}
            </button>
          </form>

          {!shouldPromptToResumeInterview && currentQuestion ? (
            <div className="question-card">
              <h3>Current Question</h3>
              <p>{currentQuestion}</p>
              <button type="button" className="button button--ghost" onClick={handlePauseInterviewToDashboard}>
                Pause and return to dashboard
              </button>

              <form onSubmit={handleSubmitAnswer} className="form">
                <label>
                  Your Answer
                  <textarea
                    value={currentAnswer}
                    onChange={(event) => setCurrentAnswer(event.target.value)}
                    rows={6}
                    placeholder="Write your interview answer..."
                    required
                    aria-describedby="hint-answer-wc"
                  />
                  <span id="hint-answer-wc" className="field-hint">
                    {answerWordCount} word{answerWordCount === 1 ? '' : 's'} (aim for ~60–120 for a strong behavioral
                    answer)
                  </span>
                </label>
                <button type="submit" className="button button--secondary" disabled={isSubmittingAnswer}>
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
              {latestFollowUpQuestion ? (
                <p className="message message--info">
                  <strong>Real-time follow-up:</strong> {latestFollowUpQuestion}
                </p>
              ) : null}
              {latestCritique ? (
                <p className="message message--info">
                  <strong>Critique:</strong> {latestCritique}
                </p>
              ) : null}
              {latestRewrite ? (
                <div className="message message--success">
                  <p>
                    <strong>Suggested rewrite:</strong>
                  </p>
                  <p>{latestRewrite}</p>
                  <div className="rewrite-audio-row">
                    <div className="rewrite-audio-controls">
                      <button
                        type="button"
                        className="button button--ghost rewrite-audio-icon-btn"
                        disabled={!speechSupported}
                        onClick={handleRewritePlayAudio}
                        aria-label="Play audio"
                      >
                        <span aria-hidden="true">{'>'}</span>
                      </button>
                      <button
                        type="button"
                        className="button button--ghost rewrite-audio-icon-btn"
                        disabled={!speechSupported}
                        onClick={handleRewritePauseAudio}
                        aria-label="Pause audio"
                      >
                        <span aria-hidden="true">||</span>
                      </button>
                      <button
                        type="button"
                        className="button button--ghost rewrite-audio-icon-btn"
                        disabled={!speechSupported}
                        onClick={handleRewriteRestartAudio}
                        aria-label="Restart audio from beginning"
                      >
                        <span aria-hidden="true">🔊</span>
                      </button>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        step="1"
                        value={Math.round(rewriteSpeechProgress)}
                        onChange={handleRewriteSeekChange}
                        onMouseUp={handleRewriteSeekCommit}
                        onTouchEnd={handleRewriteSeekCommit}
                        className="rewrite-audio-slider"
                        aria-label="Rewrite audio position"
                        disabled={!speechSupported}
                      />
                    </div>
                  </div>
                </div>
              ) : null}
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
          {debriefActions.length > 0 || nextRoundTarget || curriculumPlan.length > 0 ? (
            <div className="question-card">
              <h3>Debrief + Action Tracker</h3>
              {debriefActions.length > 0 ? (
                <ul className="history-list">
                  {debriefActions.map((action) => (
                    <li key={action}>{action}</li>
                  ))}
                </ul>
              ) : null}
              {nextRoundTarget ? (
                <p className="message message--info">
                  <strong>Next round target:</strong> {nextRoundTarget}
                </p>
              ) : null}
              {curriculumPlan.length > 0 ? (
                <>
                  <h4>Weak-Spot Curriculum</h4>
                  <ul className="history-list">
                    {curriculumPlan.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </>
              ) : null}
            </div>
          ) : null}

          {interviewError ? <p className="message message--error">{interviewError}</p> : null}
        </section>
          ) : (
        <section
          className="panel panel--outreach workspace-panel workspace-panel--outreach"
          id="panel-outreach"
          role="tabpanel"
          aria-labelledby="tab-outreach"
        >
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
              <button className="button button--secondary" type="submit" disabled={isFramingOutreach}>
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
              <button type="button" className="button button--secondary" onClick={handleCopyOutreach}>
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
      </main>
    </div>
  )
}

export default App
