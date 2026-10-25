import { useCallback, useRef, useState } from 'react'

type Language = 'hi' | 'ta'
type Step = 'capture' | 'extract' | 'offer' | 'result'
type Crop = { crop_name: string; prices: { min?: number | null; max?: number | null; modal?: number | null } }
type Comparison = { board_price: number; offered_price: number; difference: number; direction: 'below' | 'above' | 'equal'; difference_percentage: number | null }

const copy = {
  hi: {
    name: 'मंडी लेंस', subtitle: 'भाव समझने में आपकी मदद',
    capture: 'मंडी बोर्ड की फोटो लें', choose: 'फोटो चुनें', use: 'इस फोटो का उपयोग करें', retake: 'दुबारा फोटो लें',
    extract: 'बोर्ड पढ़ा जा रहा है...', select: 'अपनी फसल चुनें', boardPrice: 'बोर्ड का भाव', confirmPrice: 'बोर्ड का सही भाव चुनें', minimum: 'न्यूनतम', maximum: 'अधिकतम', modal: 'मोडल', continue: 'आगे बढ़ें',
    manual: 'भाव खुद दर्ज करें', crop: 'फसल का नाम (वैकल्पिक)', retry: 'फिर कोशिश करें',
    offer: 'उसने क्या भाव बोला?', confirmed: 'आपकी फसल', record: 'भाव बोलने के लिए दबाएं', stop: 'रिकॉर्डिंग रोकें',
    transcript: 'आपने कहा', confirm: 'सही है', typeOffer: 'भाव खुद दर्ज करें', listen: 'फिर से सुनें',
    result: 'भाव की तुलना', below: 'बोर्ड से कम', above: 'बोर्ड से ज्यादा', equal: 'दोनों भाव समान हैं',
    difference: 'अंतर', another: 'दूसरा भाव जांचें', loading: 'कृपया प्रतीक्षा करें', error: 'कुछ गलत हुआ। दोबारा कोशिश करें।',
    permission: 'कैमरा या माइक्रोफोन की अनुमति नहीं मिली। आप फोटो या भाव खुद दर्ज कर सकते हैं।',
  },
  ta: {
    name: 'மண்டி லென்ஸ்', subtitle: 'விலையைப் புரிந்துகொள்ள உதவும்',
    capture: 'மண்டி பலகையின் படத்தை எடுக்கவும்', choose: 'படத்தைத் தேர்வு செய்க', use: 'இந்தப் படத்தைப் பயன்படுத்துக', retake: 'மீண்டும் எடுக்கவும்',
    extract: 'பலகையைப் படிக்கிறது...', select: 'உங்கள் பயிரைத் தேர்வு செய்க', boardPrice: 'பலகை விலை', confirmPrice: 'பலகையின் சரியான விலையைத் தேர்வு செய்க', minimum: 'குறைந்தபட்சம்', maximum: 'அதிகபட்சம்', modal: 'மோடல்', continue: 'தொடரவும்',
    manual: 'விலையை உள்ளிடுக', crop: 'பயிர் பெயர் (விருப்பம்)', retry: 'மீண்டும் முயற்சிக்கவும்',
    offer: 'அவர் என்ன விலை சொன்னார்?', confirmed: 'உங்கள் பயிர்', record: 'விலையைப் பேச அழுத்தவும்', stop: 'பதிவை நிறுத்தவும்',
    transcript: 'நீங்கள் சொன்னது', confirm: 'சரியானது', typeOffer: 'விலையை உள்ளிடுக', listen: 'மீண்டும் கேட்கவும்',
    result: 'விலை ஒப்பீடு', below: 'பலகையை விடக் குறைவு', above: 'பலகையை விட அதிகம்', equal: 'இரு விலைகளும் சமம்',
    difference: 'வித்தியாசம்', another: 'மற்றொரு விலையைச் சரிபார்க்கவும்', loading: 'காத்திருக்கவும்', error: 'ஏதோ தவறு. மீண்டும் முயற்சிக்கவும்.',
    permission: 'கேமரா அல்லது மைக்ரோஃபோன் அனுமதி இல்லை. படத்தைத் தேர்வு செய்யவும் அல்லது விலையை உள்ளிடவும்.',
  },
} as const

const money = (value: number) => `₹${value.toLocaleString('en-IN')}`
const api = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${api}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!response.ok) throw new Error(await response.text())
  return response.json() as Promise<T>
}

function App() {
  const [language, setLanguage] = useState<Language>(() => navigator.language.startsWith('ta') ? 'ta' : 'hi')
  const t = copy[language]
  const [step, setStep] = useState<Step>('capture')
  const [image, setImage] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [crops, setCrops] = useState<Crop[]>([])
  const [crop, setCrop] = useState('')
  const [boardPrice, setBoardPrice] = useState('')
  const [offeredPrice, setOfferedPrice] = useState('')
  const [transcript, setTranscript] = useState('')
  const [comparison, setComparison] = useState<Comparison | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [recording, setRecording] = useState(false)
  const recorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])
  const audio = useRef<HTMLAudioElement | null>(null)
  const selectedCrop = crops.find(item => item.crop_name === crop.trim())

  const chooseCrop = (name: string) => {
    setCrop(name)
    const match = crops.find(item => item.crop_name === name)
    if (match) setBoardPrice(String(match.prices.modal ?? match.prices.max ?? match.prices.min ?? ''))
  }

  const selectImage = (file: File | undefined) => {
    if (!file) return
    if (!['image/jpeg', 'image/png'].includes(file.type) || file.size > 10 * 1024 * 1024) {
      setError('JPG या PNG फोटो चुनें (अधिकतम 10 MB)।'); return
    }
    if (preview) URL.revokeObjectURL(preview)
    setImage(file); setPreview(URL.createObjectURL(file)); setError('')
  }

  const runOcr = async () => {
    if (!image) return
    setBusy(true); setError('')
    try {
      const form = new FormData(); form.append('file', image); form.append('language_code', language === 'hi' ? 'hi-IN' : 'ta-IN')
      const response = await fetch(`${api}/ocr`, { method: 'POST', body: form })
      if (!response.ok) {
        const payload = await response.json().catch(() => null) as { detail?: string } | null
        throw new Error(payload?.detail || t.error)
      }
      const result = await response.json() as { crops: Crop[] }
      setCrops(result.crops); setStep('extract')
      if (!result.crops.length) setError(t.manual)
    } catch (cause) { setError(cause instanceof Error ? cause.message : t.error) } finally { setBusy(false) }
  }

  const confirmBoard = () => {
    const value = Number(boardPrice.replace(/,/g, ''))
    if (!Number.isInteger(value) || value < 0) { setError(t.error); return }
    setBoardPrice(String(value)); setStep('offer'); setError('')
  }

  const transcribe = async (blob: Blob) => {
    setBusy(true); setError('')
    try {
      const form = new FormData(); form.append('file', blob, 'offer.webm'); form.append('crop_name', crop); form.append('language_code', language === 'hi' ? 'hi-IN' : 'ta-IN')
      const response = await fetch(`${api}/speech/transcribe`, { method: 'POST', body: form })
      if (!response.ok) {
        const payload = await response.json().catch(() => null) as { detail?: string } | null
        throw new Error(payload?.detail || t.error)
      }
      const result = await response.json() as { transcript: string; extracted_price: number | null; ambiguous_prices: number[] }
      setTranscript(result.transcript)
      if (result.extracted_price !== null && result.ambiguous_prices.length === 0) setOfferedPrice(String(result.extracted_price))
      else setError(t.typeOffer)
    } catch (cause) { setError(cause instanceof Error ? cause.message : t.error) } finally { setBusy(false) }
  }

  const toggleRecording = async () => {
    if (recording) { recorder.current?.stop(); setRecording(false); return }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      chunks.current = []
      const next = new MediaRecorder(stream); recorder.current = next
      next.ondataavailable = event => chunks.current.push(event.data)
      next.onstop = () => { stream.getTracks().forEach(track => track.stop()); void transcribe(new Blob(chunks.current, { type: next.mimeType })) }
      next.start(); setRecording(true); setError('')
    } catch { setError(t.permission) }
  }

  const submitOffer = async () => {
    const value = Number(offeredPrice.replace(/,/g, ''))
    const board = Number(boardPrice)
    if (!Number.isInteger(value) || value < 0) { setError(t.error); return }
    setBusy(true); setError('')
    try {
      const result = await postJson<Comparison>('/comparison', { board_price: board, offered_price: value })
      setComparison(result); setStep('result'); void speak(result)
    }
    catch { setError(t.error) } finally { setBusy(false) }
  }

  const speak = useCallback(async (result = comparison) => {
    if (!result) return
    const phrase = language === 'hi'
      ? `बोर्ड पर ${result.board_price} रुपये लिखा है। आपको ${result.offered_price} रुपये का भाव मिला है। दोनों कीमतों में ${Math.abs(result.difference)} रुपये का अंतर है।`
      : `பலகையில் ${result.board_price} ரூபாய். உங்களுக்கு ${result.offered_price} ரூபாய் விலை கிடைத்தது. வித்தியாசம் ${Math.abs(result.difference)} ரூபாய்.`
    try {
      const response = await fetch(`${api}/speech/synthesize?text=${encodeURIComponent(phrase)}&language_code=${language === 'hi' ? 'hi-IN' : 'ta-IN'}`, { method: 'POST' })
      if (!response.ok) throw new Error()
      if (audio.current) { audio.current.src = URL.createObjectURL(await response.blob()); await audio.current.play().catch(() => undefined) }
    } catch { setError(t.error) }
  }, [comparison, language, t.error])

  const reset = () => { setStep('capture'); setImage(null); setPreview(null); setCrops([]); setCrop(''); setBoardPrice(''); setOfferedPrice(''); setTranscript(''); setComparison(null); setError('') }
  const steps = ['capture', 'extract', 'offer', 'result'] as Step[]
  const heading = step === 'capture' ? t.capture : step === 'extract' ? t.select : step === 'offer' ? t.offer : t.result

  return <main className="app-shell">
    <header className="topbar"><div><strong>{t.name}</strong><span>{t.subtitle}</span></div><select aria-label="Language" value={language} onChange={event => setLanguage(event.target.value as Language)}><option value="hi">हिन्दी</option><option value="ta">தமிழ்</option></select></header>
    <nav className="steps" aria-label="Progress">{steps.map((item, index) => <span className={steps.indexOf(step) >= index ? 'active' : ''} key={item}>{index + 1}</span>)}</nav>
    <section className="card" aria-live="polite"><p className="eyebrow">MANDI LENS</p><h1>{heading}</h1>
      {error && <div className="error" role="alert">{error}</div>}
      {busy && <div className="loading">{t.loading} <span aria-hidden="true">…</span></div>}
      {step === 'capture' && <div className="capture">
        {preview ? <img className="preview" src={preview} alt="Mandi board preview" /> : <div className="camera-mark" aria-hidden="true">▣</div>}
        <label className="button primary">{t.choose}<input hidden type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={event => selectImage(event.target.files?.[0])} /></label>
        {preview && <div className="button-row"><button className="button primary" onClick={() => void runOcr()}>{t.use}</button><button className="button secondary" onClick={() => { setImage(null); setPreview(null) }}>{t.retake}</button></div>}
      </div>}
      {step === 'extract' && <div>
        {crops.length > 0 && <><p>{t.select}</p><div className="crop-list">{crops.map(item => <button className={`crop ${crop === item.crop_name ? 'selected' : ''}`} key={item.crop_name} onClick={() => chooseCrop(item.crop_name)}><span>{item.crop_name}</span><b>{money(item.prices.modal ?? item.prices.max ?? item.prices.min ?? 0)}</b></button>)}</div></>}
        <label>{t.crop}<input list="crop-options" value={crop} onChange={event => chooseCrop(event.target.value)} placeholder={crops.length ? t.select : ''} /><datalist id="crop-options">{crops.map(item => <option key={item.crop_name} value={item.crop_name} />)}</datalist></label>
        {selectedCrop && <><p>{t.confirmPrice}</p><div className="price-options">{Object.entries(selectedCrop.prices).filter(([, value]) => value !== null && value !== undefined).map(([key, value]) => <button className={String(value) === boardPrice ? 'selected' : ''} key={key} onClick={() => setBoardPrice(String(value))}><span>{key === 'min' ? t.minimum : key === 'max' ? t.maximum : t.modal}</span><b>{money(Number(value))}</b></button>)}</div></>}
        {crops.length === 0 && <label>{t.boardPrice}<input inputMode="numeric" value={boardPrice} onChange={event => setBoardPrice(event.target.value)} placeholder="2400" /></label>}
        <button className="button primary full" onClick={confirmBoard}>{t.continue}</button><button className="text-button" onClick={() => setStep('capture')}>{t.retake}</button>
      </div>}
      {step === 'offer' && <div>
        <div className="confirmed"><span>{t.confirmed}</span><b>{crop || '—'}</b><span>{t.boardPrice}</span><strong>{money(Number(boardPrice))}</strong></div>
        <button className={`mic ${recording ? 'recording' : ''}`} onClick={() => void toggleRecording()} aria-label={recording ? t.stop : t.record}>{recording ? '■' : '●'}</button><p className="center">{recording ? t.stop : t.record}</p>
        {transcript && <div className="transcript"><span>{t.transcript}</span><b>{transcript}</b></div>}
        <label>{t.typeOffer}<input inputMode="numeric" value={offeredPrice} onChange={event => setOfferedPrice(event.target.value)} placeholder="1800" /></label><button className="button primary full" onClick={() => void submitOffer()}>{t.confirm}</button>
      </div>}
      {step === 'result' && comparison && <div className="result">
        <div className="price-grid"><div><span>{t.boardPrice}</span><b>{money(comparison.board_price)}</b></div><div><span>{t.offer}</span><b>{money(comparison.offered_price)}</b></div></div>
        <div className={`difference ${comparison.direction}`}><span>{t.difference}</span><strong>{money(Math.abs(comparison.difference))}</strong><b>{comparison.direction === 'below' ? t.below : comparison.direction === 'above' ? t.above : t.equal}</b>{comparison.difference_percentage !== null && <small>{Math.abs(comparison.difference_percentage)}%</small>}</div>
        <audio ref={audio} /><button className="button secondary full" onClick={() => void speak()}>{t.listen}</button><button className="button primary full" onClick={reset}>{t.another}</button>
      </div>}
    </section>
  </main>
}

export default App
