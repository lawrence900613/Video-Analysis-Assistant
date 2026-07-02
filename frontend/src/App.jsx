import { useEffect, useState } from "react";
import Navbar from "./components/Navbar.jsx";
import Hero from "./components/Hero.jsx";
import ResultCard from "./components/ResultCard.jsx";
import PlatformGallery from "./components/PlatformGallery.jsx";
import FeatureSection from "./components/FeatureSection.jsx";
import Footer from "./components/Footer.jsx";
import { health, parseVideo } from "./api";
import { useI18n } from "./i18n.jsx";

export default function App() {
  const { t } = useI18n();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [llmReady, setLlmReady] = useState(true);

  useEffect(() => {
    health()
      .then((h) => setLlmReady(!!h.llm_ready))
      .catch(() => {});
  }, []);

  const handleParse = async () => {
    if (!url.trim()) {
      setError(t("hero.empty_url"));
      return;
    }
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const data = await parseVideo(url.trim());
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <Navbar />
      <main>
        <Hero url={url} setUrl={setUrl} onParse={handleParse} loading={loading} error={error} />
        {result && <ResultCard result={result} url={url.trim()} llmReady={llmReady} />}
        <PlatformGallery />
        <FeatureSection />
        <ProCTA />
      </main>
      <Footer />
    </div>
  );
}

function ProCTA() {
  const { t } = useI18n();
  return (
    <section id="pricing" className="mx-auto mt-24 max-w-5xl px-4 sm:px-6">
      <div className="brand-gradient relative overflow-hidden rounded-3xl px-8 py-12 text-center text-white shadow-2xl shadow-indigo-200 sm:px-16 sm:py-16">
        <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-white/10 animate-float" />
        <div className="pointer-events-none absolute -bottom-12 -left-8 h-48 w-48 rounded-full bg-white/10 animate-float" />
        <h2 className="relative text-3xl font-extrabold sm:text-4xl">{t("cta.title")}</h2>
        <p className="relative mx-auto mt-4 max-w-xl text-indigo-50">{t("cta.sub")}</p>
        <div className="relative mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <a
            href="#home"
            className="rounded-full bg-white px-8 py-3 text-sm font-bold text-indigo-600 shadow-lg transition hover:scale-105"
          >
            {t("cta.button")}
          </a>
          <span className="text-sm text-indigo-100">{t("cta.note")}</span>
        </div>
      </div>
    </section>
  );
}
