import { useState, useRef, useEffect } from 'react'
import { Code2, Brain, Terminal, Send, Loader2, Layers, ChevronRight } from 'lucide-react'
import MonacoEditor from '@monaco-editor/react'
import axios from 'axios'

// ─── Stack Problems Data ───────────────────────────────────────────────────────
const PROBLEMS = [
  {
    id: 1,
    title: 'Valid Parentheses',
    difficulty: 'Easy',
    description:
      'Given a string s containing just the characters \'(\', \')\', \'{\', \'}\', \'[\' and \']\', determine if the input string is valid.\n\nA string is valid if:\n• Every open bracket is closed by the same type of bracket.\n• Open brackets are closed in the correct order.\n• Every close bracket has a corresponding open bracket.',
    examples: [
      { input: 's = "()"', output: 'True' },
      { input: 's = "()[]{}"', output: 'True' },
      { input: 's = "(]"', output: 'False' },
    ],
    starterCode: `def is_valid(s: str) -> bool:
    # Hint: use a stack to track open brackets
    pass
`,
  },
  {
    id: 2,
    title: 'Min Stack',
    difficulty: 'Medium',
    description:
      'Design a stack that supports push, pop, top, and retrieving the minimum element in constant time O(1).\n\nImplement the MinStack class:\n• MinStack() — initializes the stack object.\n• push(val) — pushes val onto the stack.\n• pop() — removes the top element.\n• top() — gets the top element.\n• getMin() — retrieves the minimum element.',
    examples: [
      { input: 'push(-2), push(0), push(-3)\ngetMin()', output: '-3' },
      { input: 'pop()\ntop()', output: '0' },
      { input: 'getMin()', output: '-2' },
    ],
    starterCode: `class MinStack:
    def __init__(self):
        # Hint: maintain a second stack for minimums
        pass

    def push(self, val: int) -> None:
        pass

    def pop(self) -> None:
        pass

    def top(self) -> int:
        pass

    def getMin(self) -> int:
        pass
`,
  },
  {
    id: 3,
    title: 'Daily Temperatures',
    difficulty: 'Medium',
    description:
      'Given an array of integers temperatures representing daily temperatures, return an array answer such that answer[i] is the number of days you have to wait after the i-th day to get a warmer temperature.\n\nIf there is no future day with a warmer temperature, answer[i] = 0.',
    examples: [
      { input: 'temperatures = [73,74,75,71,69,72,76,73]', output: '[1,1,4,2,1,1,0,0]' },
      { input: 'temperatures = [30,40,50,60]', output: '[1,1,1,0]' },
      { input: 'temperatures = [30,60,90]', output: '[1,1,0]' },
    ],
    starterCode: `def daily_temperatures(temperatures: list[int]) -> list[int]:
    # Hint: use a monotonic decreasing stack of indices
    pass
`,
  },
  {
    id: 4,
    title: 'Evaluate Reverse Polish Notation',
    difficulty: 'Medium',
    description:
      'Evaluate the value of an arithmetic expression in Reverse Polish Notation (RPN).\n\nValid operators are +, -, *, and /. Each operand may be an integer or another expression.\n\nNote: Division truncates toward zero.',
    examples: [
      { input: 'tokens = ["2","1","+","3","*"]', output: '9' },
      { input: 'tokens = ["4","13","5","/","+"]', output: '6' },
      { input: 'tokens = ["10","6","9","3","+","-11","*","/","*","17","+","5","+"]', output: '22' },
    ],
    starterCode: `def eval_rpn(tokens: list[str]) -> int:
    # Hint: push operands; on operator, pop two values and push result
    pass
`,
  },
]

const DIFF_COLORS = {
  Easy:   'text-[#a6e3a1]',
  Medium: 'text-[#f9e2af]',
  Hard:   'text-[#f38ba8]',
}

// ─── Problem Sidebar ───────────────────────────────────────────────────────────
function ProblemSidebar({ problems, selected, onSelect }) {
  return (
    <div className="flex flex-col w-56 shrink-0 h-full bg-[#181825] border-r border-[#313244]">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[#313244]">
        <Layers size={15} className="text-[#89b4fa]" />
        <span className="text-xs font-semibold text-[#cdd6f4] tracking-widest uppercase">Problems</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {problems.map((p) => (
          <button
            key={p.id}
            onClick={() => onSelect(p)}
            className={`w-full text-left px-4 py-3 border-b border-[#1e1e2e] transition-colors cursor-pointer ${
              selected?.id === p.id
                ? 'bg-[#313244]'
                : 'hover:bg-[#232334]'
            }`}
          >
            <div className="flex items-center justify-between gap-1">
              <span className="text-xs font-medium text-[#cdd6f4] leading-snug">{p.title}</span>
              {selected?.id === p.id && <ChevronRight size={12} className="text-[#89b4fa] shrink-0" />}
            </div>
            <span className={`text-xs mt-1 block font-semibold ${DIFF_COLORS[p.difficulty]}`}>
              {p.difficulty}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── Problem Description Panel ─────────────────────────────────────────────────
function ProblemPane({ problem }) {
  if (!problem) return null
  return (
    <div className="overflow-y-auto h-full px-5 py-4 space-y-4 text-sm text-[#cdd6f4]">
      <div>
        <div className="flex items-center gap-3 mb-1">
          <h2 className="font-bold text-[#cdd6f4] text-base">{problem.title}</h2>
          <span className={`text-xs font-semibold ${DIFF_COLORS[problem.difficulty]}`}>
            {problem.difficulty}
          </span>
        </div>
        <p className="text-[#a6adc8] leading-relaxed whitespace-pre-wrap">{problem.description}</p>
      </div>
      <div className="space-y-2">
        {problem.examples.map((ex, i) => (
          <div key={i} className="rounded-lg bg-[#11111b] border border-[#313244] p-3 font-mono text-xs space-y-1">
            <div><span className="text-[#585b70]">Input:  </span><span className="text-[#a6e3a1]">{ex.input}</span></div>
            <div><span className="text-[#585b70]">Output: </span><span className="text-[#89b4fa]">{ex.output}</span></div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Left Panel — Code Editor ─────────────────────────────────────────────────
function CodeEditorPanel({ problem, code, language, setCode, isLoading, onSubmit }) {
  return (
    <div className="flex h-full w-[60%] border-r border-[#313244]">
      {/* Problem description — left strip */}
      <div className="flex flex-col w-[45%] h-full border-r border-[#313244] bg-[#1e1e2e]">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-[#313244] bg-[#181825] shrink-0">
          <Code2 size={16} className="text-[#89b4fa]" />
          <span className="text-xs font-semibold text-[#cdd6f4] tracking-wide">Problem</span>
        </div>
        <div className="flex-1 overflow-hidden">
          <ProblemPane problem={problem} />
        </div>
      </div>

      {/* Editor — right strip */}
      <div className="flex flex-col flex-1 h-full bg-[#1e1e2e]">
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-[#313244] bg-[#181825] shrink-0">
          <Code2 size={18} className="text-[#89b4fa]" />
          <span className="text-sm font-semibold text-[#cdd6f4] tracking-wide">Code Editor</span>
          <div className="ml-auto flex gap-1.5">
            <span className="w-3 h-3 rounded-full bg-[#f38ba8]" />
            <span className="w-3 h-3 rounded-full bg-[#f9e2af]" />
            <span className="w-3 h-3 rounded-full bg-[#a6e3a1]" />
          </div>
        </div>

        {/* Monaco Editor */}
        <div className="flex-1 overflow-hidden">
          <MonacoEditor
            height="100%"
            language={language}
            theme="vs-dark"
            value={code}
            onChange={(val) => setCode(val ?? '')}
            options={{
              fontSize: 14,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              lineNumbers: 'on',
              renderLineHighlight: 'line',
              padding: { top: 16, bottom: 16 },
              fontFamily: "'Fira Code', 'JetBrains Mono', monospace",
              fontLigatures: true,
            }}
          />
        </div>

        {/* Footer — Submit */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-[#313244] bg-[#181825] shrink-0">
          <div className="flex gap-2 text-xs text-[#585b70]">
            <span className="px-2 py-1 rounded bg-[#313244] text-[#a6e3a1]">Python 3</span>
            <span className="px-2 py-1 rounded bg-[#313244]">
              {isLoading ? 'Running…' : 'Ready'}
            </span>
          </div>
          <button
            onClick={onSubmit}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#89b4fa] hover:bg-[#74c7ec] text-[#1e1e2e] text-sm font-semibold transition-colors duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <><Loader2 size={14} className="animate-spin" />Analyzing…</>
            ) : (
              <><Send size={14} />Submit</>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Top-Right Panel — Socratic Tutor ────────────────────────────────────────
function TutorPanel({ chatHistory, chatInput, setChatInput }) {
  const endRef = useRef(null)
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory])

  return (
    <div className="flex flex-col h-[70%] border-b border-[#313244]">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[#313244] bg-[#181825]">
        <Brain size={18} className="text-[#cba6f7]" />
        <span className="text-sm font-semibold text-[#cdd6f4] tracking-wide">
          Socratic Tutor
        </span>
        <span className="ml-auto flex items-center gap-1.5 text-xs text-[#a6e3a1]">
          <span className="w-2 h-2 rounded-full bg-[#a6e3a1] animate-pulse" />
          Active
        </span>
      </div>

      {/* Scrollable messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {chatHistory.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] px-3 py-2 rounded-xl text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-[#89b4fa] text-[#1e1e2e] rounded-tr-sm'
                  : 'bg-[#313244] text-[#cdd6f4] rounded-tl-sm'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {/* Input row */}
      <div className="flex items-center gap-2 px-4 py-3 border-t border-[#313244] bg-[#181825]">
        <input
          type="text"
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          placeholder="Ask a question or explain your approach…"
          className="flex-1 bg-[#313244] text-[#cdd6f4] placeholder-[#585b70] text-sm rounded-lg px-3 py-2 outline-none focus:ring-1 focus:ring-[#89b4fa] transition"
        />
        <button className="p-2 rounded-lg bg-[#cba6f7] hover:bg-[#b4befe] text-[#1e1e2e] transition-colors duration-200 cursor-pointer">
          <Send size={14} />
        </button>
      </div>
    </div>
  )
}

// ─── Bottom-Right Panel — Agent Terminal ──────────────────────────────────────
function AgentTerminal({ agentLogs }) {
  const endRef = useRef(null)
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [agentLogs])

  return (
    <div className="flex flex-col h-[30%] bg-[#11111b]">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-[#313244] bg-[#181825]">
        <Terminal size={16} className="text-[#a6e3a1]" />
        <span className="text-xs font-semibold text-[#a6e3a1] tracking-widest uppercase">
          Agent Terminal
        </span>
      </div>

      {/* Log output */}
      <div className="flex-1 overflow-y-auto px-4 py-3 font-mono text-xs text-[#a6e3a1] space-y-1 leading-5">
        {agentLogs.map((line, i) => (
          <div key={i} className={line.endsWith('_') ? 'animate-pulse' : ''}>
            {line}
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  )
}

// ─── Root App ─────────────────────────────────────────────────────────────────
function App() {
  const [selectedProblem, setSelectedProblem] = useState(PROBLEMS[0])
  const [code, setCode] = useState(PROBLEMS[0].starterCode)
  const [language] = useState('python')
  const [isLoading, setIsLoading] = useState(false)
  const [chatInput, setChatInput] = useState('')
  const [chatHistory, setChatHistory] = useState([
    {
      role: 'bot',
      content: "Hello! I'm your Socratic Tutor. Pick a problem, write your solution, and hit Submit!",
    },
  ])
  const [agentLogs, setAgentLogs] = useState([
    '> System ready. Awaiting code submission…',
    '> _',
  ])

  const handleSelectProblem = (problem) => {
    setSelectedProblem(problem)
    setCode(problem.starterCode)
    setChatHistory([
      {
        role: 'bot',
        content: `Let's tackle **${problem.title}**! Read the problem description, write your solution, then hit Submit.`,
      },
    ])
    setAgentLogs([
      `> Problem loaded: ${problem.title} [${problem.difficulty}]`,
      '> Awaiting code submission…',
      '> _',
    ])
  }

  const handleSubmitCode = async () => {
    setIsLoading(true)
    setChatHistory((prev) => [
      ...prev,
      { role: 'user', content: 'Submitted code for evaluation...' },
    ])
    setAgentLogs((prev) => [
      ...prev.filter((l) => !l.endsWith('_')),
      '> [orchestrator] Received submission. Routing to agents…',
      '> _',
    ])

    try {
      const response = await axios.post('http://localhost:8000/submit', {
        language,
        code,
        user_id: 'user_42',
      })
      const data = response.data
      if (Array.isArray(data.agent_logs) && data.agent_logs.length > 0) {
        setAgentLogs((prev) => [
          ...prev.filter((l) => !l.endsWith('_')),
          ...data.agent_logs,
          '> _',
        ])
      }
      if (data.tutor_response) {
        setChatHistory((prev) => [
          ...prev,
          { role: 'bot', content: data.tutor_response },
        ])
      }
    } catch (err) {
      const msg = err.response?.data?.detail ?? err.message ?? 'Unknown error.'
      setChatHistory((prev) => [
        ...prev,
        { role: 'bot', content: `⚠️ Error: ${msg}` },
      ])
      setAgentLogs((prev) => [
        ...prev.filter((l) => !l.endsWith('_')),
        `> [error] ${msg}`,
        '> _',
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex h-screen w-screen bg-[#1e1e2e] text-[#cdd6f4] overflow-hidden">
      {/* Problem selector sidebar */}
      <ProblemSidebar
        problems={PROBLEMS}
        selected={selectedProblem}
        onSelect={handleSelectProblem}
      />

      {/* Left — Problem description + Code Editor */}
      <CodeEditorPanel
        problem={selectedProblem}
        code={code}
        language={language}
        setCode={setCode}
        isLoading={isLoading}
        onSubmit={handleSubmitCode}
      />

      {/* Right — Tutor + Terminal */}
      <div className="flex flex-col w-[40%] h-full">
        <TutorPanel
          chatHistory={chatHistory}
          chatInput={chatInput}
          setChatInput={setChatInput}
        />
        <AgentTerminal agentLogs={agentLogs} />
      </div>
    </div>
  )
}

export default App