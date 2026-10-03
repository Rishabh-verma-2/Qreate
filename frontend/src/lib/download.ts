/**
 * Downloads a video file to the user's device by fetching its blob and
 * triggering a browser file download dialog.
 * 
 * Works for cross-origin URLs (e.g. Cloudinary) where the HTML5 `download`
 * attribute is ignored by modern browsers.
 */
export async function downloadVideoFile(url: string, suggestedFilename?: string): Promise<void> {
  const filename = suggestedFilename || `qreate_video_${Date.now()}.mp4`;
  const cleanFilename = filename.endsWith('.mp4') ? filename : `${filename}.mp4`;

  try {
    // 1. Try direct fetch blob (Cloudinary supports CORS with Access-Control-Allow-Origin: *)
    const response = await fetch(url, {
      method: 'GET',
      mode: 'cors',
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const blob = await response.blob();
    const blobUrl = window.URL.createObjectURL(blob);

    const anchor = document.createElement('a');
    anchor.style.display = 'none';
    anchor.href = blobUrl;
    anchor.download = cleanFilename;
    document.body.appendChild(anchor);
    anchor.click();

    // Clean up memory
    setTimeout(() => {
      document.body.removeChild(anchor);
      window.URL.revokeObjectURL(blobUrl);
    }, 2000);
  } catch (directErr) {
    console.warn('Direct blob download failed, trying backend download proxy:', directErr);

    // 2. Fallback: Use backend proxy which sends Content-Disposition: attachment
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const proxyUrl = `${apiBase}/api/videos/download?url=${encodeURIComponent(url)}&filename=${encodeURIComponent(cleanFilename)}`;
      
      const anchor = document.createElement('a');
      anchor.style.display = 'none';
      anchor.href = proxyUrl;
      anchor.setAttribute('download', cleanFilename);
      document.body.appendChild(anchor);
      anchor.click();

      setTimeout(() => {
        document.body.removeChild(anchor);
      }, 2000);
    } catch (proxyErr) {
      console.error('All download mechanisms failed, opening video in new tab:', proxyErr);
      window.open(url, '_blank');
    }
  }
}
