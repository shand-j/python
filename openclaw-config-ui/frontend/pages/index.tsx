import Head from 'next/head';
import Wizard from '../components/Wizard';

export default function Home() {
  return (
    <>
      <Head>
        <title>OpenClaw Setup Wizard</title>
        <meta name="description" content="Set up your OpenClaw AI assistant in minutes" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <main style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
        <div style={{ padding: '2rem 0' }}>
          <Wizard />
        </div>
      </main>
    </>
  );
}
