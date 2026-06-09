import { useCallback, useEffect, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'

// 画像／テキストを AI に渡す取り込みバー（チャット入力風）。送信処理は呼び出し側に委ねる
// （カレンダー＝新規イベント作成、イベント詳細＝そのイベントへ予定追加、で使い回す）。
export function IntakeComposer({
  submit,
}: {
  submit: (form: FormData) => Promise<void>
}) {
  const [preview, setPreview] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const formRef = useRef<HTMLFormElement>(null)

  const showFile = useCallback((file: File) => {
    setPreview(URL.createObjectURL(file))
  }, [])

  // スクショをページ上で Ctrl+V → file input にセットして一緒に送信できるようにする。
  useEffect(() => {
    function onPaste(event: ClipboardEvent) {
      const items = event.clipboardData?.items
      if (!items || !fileRef.current) return
      for (const item of Array.from(items)) {
        if (!item.type.startsWith('image/')) continue
        const file = item.getAsFile()
        if (!file) continue
        const transfer = new DataTransfer()
        transfer.items.add(file)
        fileRef.current.files = transfer.files
        showFile(file)
        event.preventDefault()
        break
      }
    }
    window.addEventListener('paste', onPaste)
    return () => window.removeEventListener('paste', onPaste)
  }, [showFile])

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (file) showFile(file)
  }

  function clearImage() {
    if (fileRef.current) fileRef.current.value = ''
    setPreview(null)
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    const form = new FormData(event.currentTarget)
    try {
      await submit(form)
      formRef.current?.reset()
      setPreview(null)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form
      ref={formRef}
      className="intake"
      onSubmit={onSubmit}
      aria-label="予定の取り込み"
      aria-busy={submitting}
    >
      {/* サムネ置き場は常設し、画像が入ったら CSS で滑らかに開く（:has） */}
      <div className="intake-media">
        {preview && (
          <div className="intake-thumbs">
            <div className="intake-thumb">
              <img
                className="preview"
                src={preview}
                alt="取り込む画像のプレビュー"
              />
              <button
                type="button"
                className="intake-thumb-x"
                aria-label="この画像を外す"
                onClick={clearImage}
              >
                ×
              </button>
            </div>
          </div>
        )}
      </div>
      <div className="intake-row">
        <label className="intake-add" aria-label="画像を追加">
          +
          <input
            ref={fileRef}
            type="file"
            name="image"
            accept="image/*"
            hidden
            onChange={onFileChange}
          />
        </label>
        <textarea
          name="text"
          aria-label="取り込むテキスト"
          placeholder="予定が書かれた画像やテキストを貼り付けてください。"
        />
        <button
          type="submit"
          className="intake-submit"
          disabled={submitting}
          aria-label="取り込む"
        >
          ↑
        </button>
      </div>
    </form>
  )
}
