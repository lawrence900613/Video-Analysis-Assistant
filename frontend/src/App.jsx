import { useEffect, useState } from "react";
import Navbar from "./components/Navbar.jsx";
import Hero from "./components/Hero.jsx";
import ResultCard from "./components/ResultCard.jsx";
import PlatformGallery from "./components/PlatformGallery.jsx";
import FeatureSection from "./components/FeatureSection.jsx";
import PricingSection from "./components/PricingSection.jsx";
import FaqSection from "./components/FaqSection.jsx";
import Footer from "./components/Footer.jsx";
import { health, parseVideo } from "./api";
import { useI18n } from "./i18n.jsx";
import { computeFlowStep } from "./utils/progress.js";

export default function App() {
  const { t } = useI18n();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [llmReady, setLlmReady] = useState(true);
  const [ffmpegAvailable, setFfmpegAvailable] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [downloaded, setDownloaded] = useState(false);

  useEffect(() => {
    health()
      .then((h) => {
        setLlmReady(!!h.llm_ready);
        setFfmpegAvailable(!!h.ffmpeg);
      })
      .catch(() => {});
  }, []);

  const runParse = async (inputUrl) => {
    const trimmed = inputUrl.trim();
    if (!trimmed) {
      setError(t("hero.empty_url"));
      return;
    }
    setError("");
    setResult(null);
    setDownloading(false);
    setDownloaded(false);
    setLoading(true);
    try {
      const data = await parseVideo(trimmed);
      setResult(data);
      setFfmpegAvailable(!!data.ffmpeg);
      setUrl(trimmed);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleParse = () => runParse(url);

  const handleDownloadStart = () => setDownloading(true);

  const handleDownloaded = () => {
    if (!result) return;
    setDownloading(false);
    setDownloaded(true);
  };

  const flowStep = computeFlowStep({ url, loading, result, downloading, downloaded });

  return (
    <div className="min-h-screen pb-20 lg:pb-0">
      <Navbar />
      <main>
        <Hero url={url} setUrl={setUrl} onParse={handleParse} loading={loading} error={error} flowStep={flowStep} />
        {result && (
          <ResultCard
            result={result}
            url={url.trim()}
            llmReady={llmReady}
            ffmpegAvailable={ffmpegAvailable}
            onDownloadStart={handleDownloadStart}
            onDownloaded={handleDownloaded}
          />
        )}
        <PlatformGallery />
        <FeatureSection />
        <PricingSection />
        <FaqSection />
      </main>
      <Footer />
    </div>
  );
}
