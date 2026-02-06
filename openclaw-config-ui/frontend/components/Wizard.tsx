import React, { useState } from 'react';
import axios from 'axios';

interface WizardStep {
  title: string;
  component: React.ReactNode;
}

interface ConfigData {
  deployment: {
    type: string;
    platform?: string;
  };
  apiKeys: {
    anthropic_key?: string;
    openai_key?: string;
    local_model?: string;
  };
  agents: Array<{
    name: string;
    model: string;
    description?: string;
    skills: string[];
  }>;
  channels: Array<{
    type: string;
    enabled: boolean;
    allowed_users: string[];
  }>;
  user_email?: string;
}

export default function Wizard() {
  const [currentStep, setCurrentStep] = useState(0);
  const [config, setConfig] = useState<ConfigData>({
    deployment: { type: 'docker' },
    apiKeys: {},
    agents: [{ name: 'Assistant', model: 'anthropic/claude-opus-4', description: '', skills: [] }],
    channels: [],
    user_email: '',
  });
  const [deploymentId, setDeploymentId] = useState<string | null>(null);
  const [deploymentStatus, setDeploymentStatus] = useState<any>(null);

  const steps: WizardStep[] = [
    {
      title: 'Welcome',
      component: <WelcomeStep />,
    },
    {
      title: 'Deployment',
      component: <DeploymentStep config={config} setConfig={setConfig} />,
    },
    {
      title: 'API Keys',
      component: <APIKeysStep config={config} setConfig={setConfig} />,
    },
    {
      title: 'Agents',
      component: <AgentsStep config={config} setConfig={setConfig} />,
    },
    {
      title: 'Channels',
      component: <ChannelsStep config={config} setConfig={setConfig} />,
    },
    {
      title: 'Review',
      component: <ReviewStep config={config} />,
    },
    {
      title: 'Deploy',
      component: <DeployStep deploymentId={deploymentId} deploymentStatus={deploymentStatus} />,
    },
  ];

  const nextStep = async () => {
    if (currentStep === steps.length - 2) {
      // Deploy step
      await handleDeploy();
    }
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleDeploy = async () => {
    try {
      const response = await axios.post('http://localhost:8000/api/deploy', config);
      setDeploymentId(response.data.deployment_id);
      
      // Poll for deployment status
      const interval = setInterval(async () => {
        const statusResponse = await axios.get(
          `http://localhost:8000/api/deployment/${response.data.deployment_id}/status`
        );
        setDeploymentStatus(statusResponse.data);
        
        if (statusResponse.data.status === 'completed' || statusResponse.data.status === 'failed') {
          clearInterval(interval);
        }
      }, 2000);
    } catch (error) {
      console.error('Deployment failed:', error);
    }
  };

  return (
    <div className="wizard-container">
      <div className="mb-8 text-center">
        <h1 className="text-4xl font-bold mb-2">OpenClaw Setup Wizard</h1>
        <p className="text-gray-600">Let's get your AI assistant up and running!</p>
      </div>

      <div className="step-indicator">
        {steps.map((step, index) => (
          <div
            key={index}
            className={`step ${index === currentStep ? 'active' : ''} ${
              index < currentStep ? 'completed' : ''
            }`}
          >
            {step.title}
          </div>
        ))}
      </div>

      <div className="card">
        {steps[currentStep].component}
        
        <div className="flex justify-between mt-8">
          <button
            onClick={prevStep}
            disabled={currentStep === 0}
            className="button-secondary"
            style={{ visibility: currentStep === 0 ? 'hidden' : 'visible' }}
          >
            Previous
          </button>
          
          {currentStep < steps.length - 1 && (
            <button onClick={nextStep} className="button-primary">
              {currentStep === steps.length - 2 ? 'Deploy Now' : 'Next'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function WelcomeStep() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Welcome to OpenClaw! 👋</h2>
      <div className="space-y-4 text-gray-700">
        <p className="text-lg">
          You're about to create your own AI-powered automation assistant. Don't worry - we'll guide you through every step!
        </p>
        
        <div className="bg-blue-50 p-4 rounded-lg">
          <h3 className="font-semibold mb-2">What you'll set up:</h3>
          <ul className="list-disc list-inside space-y-1">
            <li>Where to run your AI assistant (your computer, cloud, etc.)</li>
            <li>Which AI service to use (like ChatGPT or Claude)</li>
            <li>Your AI assistant's personality and capabilities</li>
            <li>How to communicate with it (WhatsApp, Telegram, etc.)</li>
          </ul>
        </div>

        <div className="bg-green-50 p-4 rounded-lg">
          <h3 className="font-semibold mb-2">⏱️ Time required:</h3>
          <p>About 5-10 minutes to complete the setup</p>
        </div>

        <p className="text-sm text-gray-600 italic">
          This wizard is designed to be super simple - even if you've never done anything like this before, you'll be able to follow along!
        </p>
      </div>
    </div>
  );
}

function DeploymentStep({ config, setConfig }: any) {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Where should we set this up?</h2>
      <p className="text-gray-700 mb-6">
        Choose where you want to run your AI assistant. Don't worry - we'll explain each option!
      </p>

      <div className="space-y-4">
        <label className="block p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50">
          <input
            type="radio"
            name="deployment"
            value="docker"
            checked={config.deployment.type === 'docker'}
            onChange={(e) => setConfig({ ...config, deployment: { type: e.target.value } })}
            className="mr-3"
          />
          <div className="inline-block">
            <span className="font-semibold text-lg">🐳 Docker (Recommended)</span>
            <p className="text-sm text-gray-600 mt-1">
              Easiest option! Works on any computer. Like installing a regular app.
            </p>
          </div>
        </label>

        <label className="block p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50">
          <input
            type="radio"
            name="deployment"
            value="serverless"
            checked={config.deployment.type === 'serverless'}
            onChange={(e) => setConfig({ ...config, deployment: { type: e.target.value } })}
            className="mr-3"
          />
          <div className="inline-block">
            <span className="font-semibold text-lg">☁️ Cloud (Serverless)</span>
            <p className="text-sm text-gray-600 mt-1">
              Run in the cloud without managing servers. Good for always-on access.
            </p>
          </div>
        </label>

        <label className="block p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50">
          <input
            type="radio"
            name="deployment"
            value="direct"
            checked={config.deployment.type === 'direct'}
            onChange={(e) => setConfig({ ...config, deployment: { type: e.target.value } })}
            className="mr-3"
          />
          <div className="inline-block">
            <span className="font-semibold text-lg">💻 Direct Install</span>
            <p className="text-sm text-gray-600 mt-1">
              Install directly on your computer. Good if you're comfortable with terminal commands.
            </p>
          </div>
        </label>
      </div>
    </div>
  );
}

function APIKeysStep({ config, setConfig }: any) {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Connect your AI service</h2>
      <p className="text-gray-700 mb-6">
        To use AI, you need an API key from a service like Anthropic (Claude) or OpenAI (ChatGPT).
      </p>

      <div className="bg-yellow-50 p-4 rounded-lg mb-6">
        <h3 className="font-semibold mb-2">📝 Getting your API key:</h3>
        <ul className="list-disc list-inside space-y-1 text-sm">
          <li>Anthropic Claude: Visit <a href="https://console.anthropic.com/" className="text-blue-600 underline" target="_blank">console.anthropic.com</a></li>
          <li>OpenAI: Visit <a href="https://platform.openai.com/api-keys" className="text-blue-600 underline" target="_blank">platform.openai.com/api-keys</a></li>
        </ul>
      </div>

      <div className="space-y-4">
        <div>
          <label className="label">Anthropic API Key (Recommended)</label>
          <input
            type="password"
            className="input-field"
            placeholder="sk-ant-..."
            value={config.apiKeys.anthropic_key || ''}
            onChange={(e) => setConfig({
              ...config,
              apiKeys: { ...config.apiKeys, anthropic_key: e.target.value }
            })}
          />
          <p className="help-text">Claude is great for complex tasks and long conversations</p>
        </div>

        <div>
          <label className="label">OpenAI API Key (Alternative)</label>
          <input
            type="password"
            className="input-field"
            placeholder="sk-..."
            value={config.apiKeys.openai_key || ''}
            onChange={(e) => setConfig({
              ...config,
              apiKeys: { ...config.apiKeys, openai_key: e.target.value }
            })}
          />
          <p className="help-text">ChatGPT is fast and great for general tasks</p>
        </div>

        <div>
          <label className="label">Local Model (Advanced - Optional)</label>
          <input
            type="text"
            className="input-field"
            placeholder="llama2, mistral, etc."
            value={config.apiKeys.local_model || ''}
            onChange={(e) => setConfig({
              ...config,
              apiKeys: { ...config.apiKeys, local_model: e.target.value }
            })}
          />
          <p className="help-text">Run AI locally on your computer (requires Ollama)</p>
        </div>
      </div>
    </div>
  );
}

function AgentsStep({ config, setConfig }: any) {
  const agent = config.agents[0];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Configure your AI assistant</h2>
      <p className="text-gray-700 mb-6">
        Let's give your assistant a name and choose which AI model to use.
      </p>

      <div className="space-y-4">
        <div>
          <label className="label">Assistant Name</label>
          <input
            type="text"
            className="input-field"
            placeholder="e.g., Dorothy's Helper, Work Assistant"
            value={agent.name}
            onChange={(e) => {
              const newAgents = [...config.agents];
              newAgents[0].name = e.target.value;
              setConfig({ ...config, agents: newAgents });
            }}
          />
          <p className="help-text">Give your assistant a friendly name</p>
        </div>

        <div>
          <label className="label">AI Model</label>
          <select
            className="input-field"
            value={agent.model}
            onChange={(e) => {
              const newAgents = [...config.agents];
              newAgents[0].model = e.target.value;
              setConfig({ ...config, agents: newAgents });
            }}
          >
            <option value="anthropic/claude-opus-4">Claude Opus (Most Capable)</option>
            <option value="anthropic/claude-sonnet-3-5">Claude Sonnet (Balanced)</option>
            <option value="openai/gpt-4-turbo">GPT-4 Turbo (Fast & Smart)</option>
            <option value="openai/gpt-4">GPT-4 (Reliable)</option>
            <option value="openai/gpt-3.5-turbo">GPT-3.5 (Fastest & Cheapest)</option>
          </select>
          <p className="help-text">More capable models cost more but give better results</p>
        </div>

        <div>
          <label className="label">Description (Optional)</label>
          <textarea
            className="input-field"
            rows={3}
            placeholder="e.g., Helps me automate my daily tasks and manage my workflow"
            value={agent.description || ''}
            onChange={(e) => {
              const newAgents = [...config.agents];
              newAgents[0].description = e.target.value;
              setConfig({ ...config, agents: newAgents });
            }}
          />
          <p className="help-text">Describe what you want your assistant to help with</p>
        </div>
      </div>
    </div>
  );
}

function ChannelsStep({ config, setConfig }: any) {
  const toggleChannel = (type: string) => {
    const existingChannel = config.channels.find((c: any) => c.type === type);
    
    if (existingChannel) {
      setConfig({
        ...config,
        channels: config.channels.filter((c: any) => c.type !== type)
      });
    } else {
      setConfig({
        ...config,
        channels: [...config.channels, { type, enabled: true, allowed_users: [] }]
      });
    }
  };

  const isChannelEnabled = (type: string) => {
    return config.channels.some((c: any) => c.type === type);
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">How do you want to chat?</h2>
      <p className="text-gray-700 mb-6">
        Choose how you want to communicate with your AI assistant. You can select multiple options!
      </p>

      <div className="space-y-3">
        <label className="flex items-center p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50">
          <input
            type="checkbox"
            checked={isChannelEnabled('whatsapp')}
            onChange={() => toggleChannel('whatsapp')}
            className="mr-3 w-5 h-5"
          />
          <div>
            <span className="font-semibold text-lg">💬 WhatsApp</span>
            <p className="text-sm text-gray-600">Chat with your assistant via WhatsApp</p>
          </div>
        </label>

        <label className="flex items-center p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50">
          <input
            type="checkbox"
            checked={isChannelEnabled('telegram')}
            onChange={() => toggleChannel('telegram')}
            className="mr-3 w-5 h-5"
          />
          <div>
            <span className="font-semibold text-lg">✈️ Telegram</span>
            <p className="text-sm text-gray-600">Use Telegram to communicate</p>
          </div>
        </label>

        <label className="flex items-center p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50">
          <input
            type="checkbox"
            checked={isChannelEnabled('slack')}
            onChange={() => toggleChannel('slack')}
            className="mr-3 w-5 h-5"
          />
          <div>
            <span className="font-semibold text-lg">💼 Slack</span>
            <p className="text-sm text-gray-600">Integrate with your work Slack</p>
          </div>
        </label>

        <label className="flex items-center p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50">
          <input
            type="checkbox"
            checked={isChannelEnabled('discord')}
            onChange={() => toggleChannel('discord')}
            className="mr-3 w-5 h-5"
          />
          <div>
            <span className="font-semibold text-lg">🎮 Discord</span>
            <p className="text-sm text-gray-600">Use Discord for communication</p>
          </div>
        </label>
      </div>

      {config.channels.length === 0 && (
        <div className="bg-yellow-50 p-4 rounded-lg mt-4">
          <p className="text-sm">⚠️ Please select at least one communication channel</p>
        </div>
      )}
    </div>
  );
}

function ReviewStep({ config }: any) {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Ready to deploy! 🚀</h2>
      <p className="text-gray-700 mb-6">
        Let's review your configuration before we deploy.
      </p>

      <div className="space-y-4">
        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="font-semibold mb-2">Deployment Method</h3>
          <p className="capitalize">{config.deployment.type}</p>
        </div>

        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="font-semibold mb-2">AI Provider</h3>
          <p>
            {config.apiKeys.anthropic_key ? '✓ Anthropic Claude' : ''}
            {config.apiKeys.openai_key ? ' ✓ OpenAI' : ''}
            {config.apiKeys.local_model ? ` ✓ Local (${config.apiKeys.local_model})` : ''}
          </p>
        </div>

        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="font-semibold mb-2">Assistant</h3>
          <p><strong>Name:</strong> {config.agents[0]?.name}</p>
          <p><strong>Model:</strong> {config.agents[0]?.model}</p>
        </div>

        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="font-semibold mb-2">Communication Channels</h3>
          {config.channels.length > 0 ? (
            <ul className="list-disc list-inside">
              {config.channels.map((channel: any, index: number) => (
                <li key={index} className="capitalize">{channel.type}</li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-600 italic">No channels configured</p>
          )}
        </div>
      </div>

      <div className="bg-blue-50 p-4 rounded-lg mt-6">
        <p className="text-sm">
          ℹ️ Click "Deploy Now" to set up your AI assistant. This will take a few minutes.
        </p>
      </div>
    </div>
  );
}

function DeployStep({ deploymentId, deploymentStatus }: any) {
  if (!deploymentStatus) {
    return (
      <div className="text-center">
        <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-4"></div>
        <p className="text-lg">Starting deployment...</p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">
        {deploymentStatus.status === 'completed' ? '🎉 All Done!' : 'Deploying...'}
      </h2>
      
      <div className="space-y-4">
        <div className="progress-bar">
          <div
            className="progress-bar-fill"
            style={{ width: `${deploymentStatus.progress}%` }}
          />
        </div>

        <p className="text-center text-lg">{deploymentStatus.message}</p>
        <p className="text-center text-gray-600">{deploymentStatus.progress}% complete</p>

        {deploymentStatus.status === 'completed' && (
          <div className="bg-green-50 p-6 rounded-lg mt-6">
            <h3 className="font-semibold text-lg mb-4">🎊 Success! Your AI assistant is ready!</h3>
            
            <div className="space-y-3 text-sm">
              <h4 className="font-semibold">Next steps:</h4>
              <ol className="list-decimal list-inside space-y-2">
                <li>Open your chosen messaging app (WhatsApp, Telegram, etc.)</li>
                <li>Add the bot/assistant using the connection details sent to your email</li>
                <li>Start chatting and let your AI assistant help automate your work!</li>
              </ol>
            </div>

            <div className="mt-6 p-4 bg-white rounded border-2 border-green-200">
              <p className="font-semibold mb-2">Deployment ID:</p>
              <code className="text-sm bg-gray-100 p-2 rounded block">{deploymentId}</code>
              <p className="text-xs text-gray-600 mt-2">Save this ID for your records</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
