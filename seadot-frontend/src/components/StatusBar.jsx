import { motion } from 'framer-motion';
import { formatSpeed } from '../utils/format';

export default function StatusBar({ totalSpeed, activeCount, clipboardEnabled, bandwidthLimit }) {
  const bars = Array.from({ length: 18 }, (_, index) => index);
  const speedMbPerSecond = totalSpeed / (1024 * 1024);
  const speedLevel = Math.min(1, Math.log2(1 + speedMbPerSecond) / Math.log2(51));
  const isDownloading = activeCount > 0 && totalSpeed > 0;
  const animationDuration = 1.8 - speedLevel * 0.9;

  return (
    <footer className="status-bar flex h-9 shrink-0 items-center justify-between border-t border-white/10 bg-black/40 px-4 text-xs text-slate-400 backdrop-blur-xl">
      <div className="flex items-center gap-3">
        <div className="flex h-4 items-end gap-[2px]">
          {bars.map((index) => (
            <motion.span
              key={index}
              className="w-[3px] rounded-sm bg-gradient-to-t from-violet-500 to-cyan-300"
              animate={{
                height: isDownloading ? [3, 3 + speedLevel * (6 + ((index * 7) % 10)), 3] : 3,
                opacity: isDownloading ? [0.3, 0.45 + speedLevel * 0.5, 0.3] : 0.2,
              }}
              transition={{
                duration: animationDuration,
                repeat: isDownloading ? Infinity : 0,
                delay: isDownloading ? index * (0.025 + (1 - speedLevel) * 0.025) : 0,
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>
        <span>
          Total Speed: <span className="font-semibold text-cyan-300">{formatSpeed(totalSpeed)}</span>
        </span>
      </div>

      <div className="flex items-center gap-4">
        <span>{activeCount} active</span>
        <span>Limit: {bandwidthLimit === 0 ? 'Unlimited' : `${bandwidthLimit} MB/s`}</span>
        <span className={clipboardEnabled ? 'text-emerald-300' : ''}>
          Clipboard {clipboardEnabled ? 'on' : 'off'}
        </span>
      </div>
    </footer>
  );
}
