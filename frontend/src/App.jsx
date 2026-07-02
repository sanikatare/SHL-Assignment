import { useState } from 'react'
import Sidebar from './components/Sidebar'
import MobileHeader from './components/MobileHeader'
import ChatWindow from './components/ChatWindow'
import InputBar from './components/InputBar'
import { useChat } from './hooks/useChat'
import { useDarkMode } from './hooks/useDarkMode'
import { useHealthCheck } from './hooks/useHealthCheck'
import { ToastProvider, useToast } from './context/ToastContext'

function AppShell() {
  const [isDark, setIsDark] = useDarkMode()
  const [isSidebarOpen, setSidebarOpen] = useState(false)
  const healthStatus = useHealthCheck()
  const toast = useToast()

  const {
    messages,
    isLoading,
    error,
    sendMessage,
    retryLastMessage,
    clearChat,
    isEndOfConversation,
    streamingMessageId,
    finishStreaming,
  } = useChat()

  const handleSend = async (text) => {
    await sendMessage(text)
  }

  const handleClearChat = () => {
    clearChat()
    toast.info('Conversation cleared')
    setSidebarOpen(false)
  }

  const handleSelectPrompt = (text) => {
    handleSend(text)
    setSidebarOpen(false)
  }

  return (
    <div className="flex h-screen overflow-hidden bg-paper text-ink dark:bg-night-bg dark:text-night-ink">
      <Sidebar
        isDark={isDark}
        setIsDark={setIsDark}
        onClearChat={handleClearChat}
        hasMessages={messages.length > 0}
        healthStatus={healthStatus}
        isOpen={isSidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onSelectPrompt={handleSelectPrompt}
        isLoading={isLoading}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <MobileHeader onOpenMenu={() => setSidebarOpen(true)} />

        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          error={error}
          onRetry={retryLastMessage}
          streamingMessageId={streamingMessageId}
          finishStreaming={finishStreaming}
          onSelectPrompt={handleSelectPrompt}
        />

        <InputBar onSend={handleSend} disabled={isLoading} endOfConversation={isEndOfConversation} />
      </div>
    </div>
  )
}

export default function App() {
  return (
    <ToastProvider>
      <AppShell />
    </ToastProvider>
  )
}
