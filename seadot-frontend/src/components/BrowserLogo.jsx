const BROWSER_NAMES = {
  chrome: 'Google Chrome',
  edge: 'Microsoft Edge',
  firefox: 'Mozilla Firefox',
  opera: 'Opera',
};

export default function BrowserLogo({ browser }) {
  const label = BROWSER_NAMES[browser];

  return (
    <svg
      aria-label={`${label} logo`}
      role="img"
      viewBox="0 0 32 32"
      className="h-7 w-7 shrink-0"
      fill="none"
    >
      {browser === 'chrome' && (
        <>
          <circle cx="16" cy="16" r="15" fill="#34A853" />
          <path d="M1.9 8.5A15 15 0 0 1 29 8H15.1a8.1 8.1 0 0 0-7 4.1L1.9 8.5Z" fill="#EA4335" />
          <path d="M29 8a15 15 0 0 1-13 23l7-12.1a8.1 8.1 0 0 0-7-10.9H29Z" fill="#FBBC04" />
          <circle cx="16" cy="16" r="7.1" fill="white" />
          <circle cx="16" cy="16" r="5.7" fill="#4285F4" />
        </>
      )}
      {browser === 'edge' && (
        <>
          <defs>
            <linearGradient id="edge-blue" x1="4" x2="28" y1="27" y2="7" gradientUnits="userSpaceOnUse">
              <stop stopColor="#0C59A4" />
              <stop offset="1" stopColor="#1B9DE2" />
            </linearGradient>
            <linearGradient id="edge-green" x1="6" x2="27" y1="7" y2="25" gradientUnits="userSpaceOnUse">
              <stop stopColor="#35C998" />
              <stop offset="1" stopColor="#0C8A78" />
            </linearGradient>
          </defs>
          <path d="M28.7 20.2c-.9 6.1-5.7 10.1-12.4 10.1C7.8 30.3 2 24.2 2 16.4 2 8.7 8 2 16.2 2c6.3 0 11.5 4.2 12.4 10.2-2-3.1-5.2-4.8-9-4.8-5.7 0-9.8 3.9-10.5 9.1 1.8-2.2 4.2-3.3 7.4-3.3 6.2 0 10.2 2.8 12.2 7Z" fill="url(#edge-blue)" />
          <path d="M9.1 16.5c1.1-4.2 4.9-7.1 9.8-7.1 3.8 0 7 1.7 9.3 4.8.1.6.2 1.2.2 1.8 0 1.5-.2 2.9-.6 4.2-1.5-3.1-4.3-4.7-8.2-4.7-3.9 0-7.2 1.5-10.5 4.8-1.4 1.4-2.2 3-2.5 4.8-2-2.2-3.2-5.2-3.2-8.6 0-1 .1-2 .3-2.9.8-4.6 3.6-8.5 7.6-10.5-2.5 3.2-3.3 6.6-2.2 10.2Z" fill="url(#edge-green)" />
        </>
      )}
      {browser === 'firefox' && (
        <>
          <defs>
            <linearGradient id="firefox-purple" x1="4" x2="27" y1="28" y2="4" gradientUnits="userSpaceOnUse">
              <stop stopColor="#6D2ED5" />
              <stop offset=".55" stopColor="#A235D3" />
              <stop offset="1" stopColor="#FF7139" />
            </linearGradient>
            <linearGradient id="firefox-orange" x1="9" x2="25" y1="7" y2="25" gradientUnits="userSpaceOnUse">
              <stop stopColor="#FFCE45" />
              <stop offset=".55" stopColor="#FF7139" />
              <stop offset="1" stopColor="#E33B72" />
            </linearGradient>
          </defs>
          <path d="M27.3 9.1c2.8 3.2 3.6 7.8 1.8 12.1-2.3 5.7-8.9 9.4-15.2 7.4C7.5 26.8 3 21 3.2 14.6c.1-3.7 1.6-7.1 4-9.4-.2 2.8.5 4.3 1.5 5.2.7-3.5 2.7-6.2 5.7-8.2-.4 2.2.3 3.4 1.8 4.3 1.8-1.6 3.8-2.4 6-2.4-.7 1.3-.9 2.6-.5 3.8 1.6-.2 3-.1 4.2.5-.7.1-1.6.3-2.6.8Z" fill="url(#firefox-purple)" />
          <path d="M25.1 12.1c-2.3.2-4.5 1.3-6.2 3.3 2.9-.8 5.5-.4 7.8 1.1-1.1.1-2.1.4-3 .9 1.9.7 3.1 1.9 3.5 3.6-1.3-.7-2.7-1-4.4-.8 1.1 1 1.5 2.2 1.2 3.5-2.2-1.9-4.7-2.6-7.3-2.1-3.9.8-7.5-1.5-8.5-5.2-.6-2.2-.1-4.5 1.3-6.1-.1 2.2.8 3.7 2.5 4.5.2-2.5 1.8-4.3 4.2-5.3-.5 1.8.1 3.1 1.6 3.8 1.7-1.5 3.9-2.1 6.3-1.2.4 0 .8 0 1-.1Z" fill="url(#firefox-orange)" />
        </>
      )}
      {browser === 'opera' && (
        <path
          d="M16 2.2c-7.5 0-12.9 5.8-12.9 13.8S8.5 29.8 16 29.8s12.9-5.8 12.9-13.8S23.5 2.2 16 2.2Zm0 5.2c4.1 0 6.8 3.5 6.8 8.6s-2.7 8.6-6.8 8.6-6.8-3.5-6.8-8.6 2.7-8.6 6.8-8.6Z"
          fill="#FF1B2D"
        />
      )}
    </svg>
  );
}
