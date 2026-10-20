import { File, FileArchive, FileAudio, FileImage, FileText, FileVideo } from 'lucide-react';
import { fileExtension } from '../utils/format';

const GROUPS = {
  video: { Icon: FileVideo, className: 'text-violet-300' },
  archive: { Icon: FileArchive, className: 'text-cyan-300' },
  image: { Icon: FileImage, className: 'text-emerald-300' },
  audio: { Icon: FileAudio, className: 'text-orange-300' },
  document: { Icon: FileText, className: 'text-sky-300' },
  executable: { Icon: File, className: 'text-amber-300' },
};

function groupFor(ext) {
  if (['MP4', 'MKV', 'AVI', 'MOV', 'WEBM'].includes(ext)) return 'video';
  if (['ZIP', 'RAR', '7Z', 'TAR', 'GZ', 'ISO'].includes(ext)) return 'archive';
  if (['PNG', 'JPG', 'JPEG', 'GIF', 'WEBP', 'SVG'].includes(ext)) return 'image';
  if (['MP3', 'WAV', 'FLAC', 'AAC', 'OGG'].includes(ext)) return 'audio';
  if (['PDF', 'TXT', 'MD', 'DOC', 'DOCX'].includes(ext)) return 'document';
  if (['EXE', 'MSI', 'DMG', 'APP'].includes(ext)) return 'executable';
  return 'executable';
}

export default function FileTypeIcon({ name }) {
  const ext = fileExtension(name);
  const group = GROUPS[groupFor(ext)];
  const Icon = group.Icon;

  return (
    <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/5">
      <Icon className={`h-4 w-4 ${group.className}`} />
      <span className="file-extension-label absolute -bottom-1 rounded bg-[#0F0F11] px-1 text-[9px] font-semibold tracking-wide text-slate-400">
        {ext}
      </span>
    </div>
  );
}
