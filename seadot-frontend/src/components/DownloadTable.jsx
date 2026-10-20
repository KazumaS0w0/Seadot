import { AnimatePresence, motion } from 'framer-motion';
import { ArrowDown, ArrowDownUp, ArrowUp, Download, GripVertical, Zap } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import FileTypeIcon from './FileTypeIcon';
import { formatBytes, formatEta, formatSpeed } from '../utils/format';

const COLUMN_DEFINITIONS = [
  { id: 'selection', label: 'Selection', width: 44, min: 44, max: 44 },
  { id: 'name', label: 'File Name', width: 220, min: 180, max: 600 },
  { id: 'size', label: 'Size', width: 80, min: 75, max: 220 },
  { id: 'progress', label: 'Progress', width: 160, min: 130, max: 400 },
  { id: 'eta', label: 'Time Left', width: 100, min: 80, max: 220, responsive: true },
  { id: 'date', label: 'Download Date', width: 130, min: 110, max: 260 },
];

const DEFAULT_COLUMN_ORDER = ['name', 'size', 'progress', 'eta', 'date'];
const SORTABLE_COLUMNS = new Set(['name', 'size', 'progress', 'date']);

const STATUS_STYLES = {
  downloading: 'text-cyan-300',
  paused: 'text-amber-300',
  queued: 'text-violet-300',
  completed: 'text-emerald-300',
  failed: 'text-rose-300',
};

function ProgressCell({ item }) {
  const active = item.status === 'downloading';
  return (
    <div className="w-full min-w-0">
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <motion.div
          className={`h-full rounded-full ${
            item.status === 'completed'
              ? 'bg-gradient-to-r from-emerald-400 to-cyan-400'
              : 'bg-gradient-to-r from-violet-500 via-cyan-400 to-emerald-400'
          }`}
          initial={false}
          animate={{ width: `${item.progress}%` }}
          transition={{ duration: 0.35 }}
        />
      </div>
      <div className="mt-1.5 flex items-center gap-2 text-[11px] text-slate-400">
        <span className="font-medium text-slate-200">{item.progress}%</span>
        {active && (
          <span className="inline-flex items-center gap-1 text-cyan-300">
            <Zap className="h-3 w-3" />
            {formatSpeed(item.speedBps)}
          </span>
        )}
      </div>
    </div>
  );
}

export default function DownloadTable({
  items,
  selectedIds,
  onToggleSelect,
  onToggleAll,
  onOpenDetails,
}) {
  const allSelected = items.length > 0 && items.every((item) => selectedIds.includes(item.id));
  const [sort, setSort] = useState({ column: null, direction: 'ascending' });
  const [columnOrder, setColumnOrder] = useState(() => {
    try {
      const savedOrder = JSON.parse(window.localStorage.getItem('seadot-download-column-order') || 'null');
      if (
        Array.isArray(savedOrder)
        && savedOrder.length === DEFAULT_COLUMN_ORDER.length
        && new Set(savedOrder).size === DEFAULT_COLUMN_ORDER.length
        && savedOrder.every((id) => DEFAULT_COLUMN_ORDER.includes(id))
      ) {
        return savedOrder;
      }
    } catch {
      window.localStorage.removeItem('seadot-download-column-order');
    }
    return DEFAULT_COLUMN_ORDER;
  });
  const [columnWidths, setColumnWidths] = useState(() => (
    Object.fromEntries(COLUMN_DEFINITIONS.map(({ id, width }) => [id, width]))
  ));
  const [showSecondaryColumns, setShowSecondaryColumns] = useState(
    () => window.matchMedia('(min-width: 1280px)').matches,
  );
  const activeResize = useRef(null);
  const draggedColumn = useRef(null);
  const orderedColumns = columnOrder.map((id) => COLUMN_DEFINITIONS.find((column) => column.id === id));
  const sortedItems = [...items].sort((left, right) => {
    if (!sort.column) return 0;

    let comparison = 0;
    if (sort.column === 'name') {
      comparison = left.name.localeCompare(right.name, undefined, { numeric: true, sensitivity: 'base' });
    } else if (sort.column === 'size') {
      comparison = (left.sizeBytes || 0) - (right.sizeBytes || 0);
    } else if (sort.column === 'progress') {
      comparison = (left.progress || 0) - (right.progress || 0);
    } else if (sort.column === 'date') {
      comparison = String(left.dateAdded || '').localeCompare(String(right.dateAdded || ''));
    }

    return sort.direction === 'ascending' ? comparison : -comparison;
  });
  const tableWidth = COLUMN_DEFINITIONS.reduce(
    (total, column) => total + (column.responsive && !showSecondaryColumns ? 0 : columnWidths[column.id]),
    0,
  );

  useEffect(() => {
    const media = window.matchMedia('(min-width: 1280px)');
    const onChange = (event) => setShowSecondaryColumns(event.matches);
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, []);

  const resizeColumn = (columnId, delta) => {
    const column = COLUMN_DEFINITIONS.find(({ id }) => id === columnId);
    if (!column || column.min === column.max) return;

    setColumnWidths((widths) => ({
      ...widths,
      [columnId]: Math.min(column.max, Math.max(column.min, widths[columnId] + delta)),
    }));
  };

  const startResize = (event, column) => {
    event.preventDefault();
    activeResize.current = {
      columnId: column.id,
      startX: event.clientX,
      startWidth: columnWidths[column.id],
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const updateResize = (event) => {
    if (!activeResize.current) return;
    const { columnId, startX, startWidth } = activeResize.current;
    const column = COLUMN_DEFINITIONS.find(({ id }) => id === columnId);
    const width = Math.min(column.max, Math.max(column.min, startWidth + event.clientX - startX));
    setColumnWidths((widths) => ({ ...widths, [columnId]: width }));
  };

  const endResize = () => {
    activeResize.current = null;
  };

  const moveColumn = (targetId) => {
    const sourceId = draggedColumn.current;
    draggedColumn.current = null;
    if (!sourceId || sourceId === targetId) return;

    setColumnOrder((current) => {
      const next = current.filter((id) => id !== sourceId);
      next.splice(next.indexOf(targetId), 0, sourceId);
      window.localStorage.setItem('seadot-download-column-order', JSON.stringify(next));
      return next;
    });
  };

  return (
    <div className="h-full min-h-0 overflow-auto p-3 sm:p-5">
      <div className="download-table-shell min-h-full overflow-hidden rounded-2xl border border-white/10 bg-[#11141d]/70 shadow-[0_0_40px_rgba(8,10,20,0.3)]">
        <table
          className="w-full table-fixed border-collapse text-left text-sm"
          style={{ width: `max(100%, ${tableWidth}px)` }}
        >
          <colgroup>
            {[COLUMN_DEFINITIONS[0], ...orderedColumns].map((column) => (
              <col
                key={column.id}
                className={column.responsive ? 'hidden xl:table-column' : ''}
                style={{ width: `${columnWidths[column.id]}px` }}
              />
            ))}
          </colgroup>
          <thead className="table-header sticky top-0 z-10 bg-[#0B0F19]/90 text-[11px] uppercase tracking-[0.14em] text-slate-500 backdrop-blur-xl">
            <tr>
              <th className="relative px-3 py-3">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={onToggleAll}
                  className="accent-violet-500"
                />
              </th>
              {orderedColumns.map((column) => (
                <th
                  key={column.id}
                  draggable
                  onDragStart={(event) => {
                    draggedColumn.current = column.id;
                    event.dataTransfer.effectAllowed = 'move';
                    event.dataTransfer.setData('text/plain', column.id);
                  }}
                  onDragOver={(event) => {
                    event.preventDefault();
                    event.dataTransfer.dropEffect = 'move';
                  }}
                  onDrop={(event) => {
                    event.preventDefault();
                    moveColumn(column.id);
                  }}
                  onDragEnd={() => {
                    draggedColumn.current = null;
                  }}
                  className={`column-header relative whitespace-nowrap px-3 py-3 ${column.responsive ? 'hidden xl:table-cell' : ''}`}
                >
                    <GripVertical className="mr-1 inline h-3 w-3 cursor-grab opacity-35" />
                    {SORTABLE_COLUMNS.has(column.id) ? (
                      <button
                        type="button"
                        aria-label={`Sort by ${column.label}`}
                        aria-sort={sort.column === column.id ? sort.direction : 'none'}
                        onClick={() => setSort((current) => ({
                          column: column.id,
                          direction: current.column === column.id && current.direction === 'ascending'
                            ? 'descending'
                            : 'ascending',
                        }))}
                        className={`inline-flex items-center gap-1.5 pr-3 transition-colors hover:text-violet-300 ${
                          sort.column === column.id ? 'text-violet-300' : ''
                        }`}
                      >
                        {column.label}
                        {sort.column !== column.id ? (
                          <ArrowDownUp className="h-3 w-3 opacity-50" />
                        ) : sort.direction === 'ascending' ? (
                          <ArrowUp className="h-3 w-3" />
                        ) : (
                          <ArrowDown className="h-3 w-3" />
                        )}
                      </button>
                    ) : column.label}
                    <button
                    type="button"
                    aria-label={`Resize ${column.label} column`}
                    aria-orientation="vertical"
                    title={`Drag to resize ${column.label}; double-click to reset`}
                    className="column-resizer absolute right-0 top-0 z-20 h-full w-3 cursor-col-resize touch-none"
                    onPointerDown={(event) => startResize(event, column)}
                    onPointerMove={updateResize}
                    onPointerUp={endResize}
                    onPointerCancel={endResize}
                    onKeyDown={(event) => {
                      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
                      event.preventDefault();
                      resizeColumn(column.id, event.key === 'ArrowRight' ? 12 : -12);
                    }}
                    onDoubleClick={() => setColumnWidths((widths) => ({
                      ...widths,
                      [column.id]: column.width,
                    }))}
                  >
                    <span className="column-resizer-line" />
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <AnimatePresence initial={false}>
              {sortedItems.map((item) => {
                const selected = selectedIds.includes(item.id);
                return (
                  <motion.tr
                    key={item.id}
                    layout
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.98 }}
                    onClick={() => onToggleSelect(item.id)}
                    onDoubleClick={() => onOpenDetails(item)}
                    className={`h-[68px] cursor-pointer border-t border-white/5 transition-colors hover:bg-violet-500/[0.07] ${
                      selected ? 'bg-violet-500/10' : ''
                    }`}
                  >
                    <td className="px-3 py-3">
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() => onToggleSelect(item.id)}
                        onClick={(event) => event.stopPropagation()}
                        className="accent-violet-500"
                      />
                    </td>
                    {orderedColumns.map((column) => {
                      if (column.id === 'name') {
                        return (
                          <td key={column.id} className="px-3 py-3">
                            <div className="flex items-center gap-3">
                              <FileTypeIcon name={item.name} />
                              <div className="min-w-0">
                                <p className="truncate font-medium text-slate-100">{item.name}</p>
                                <p className={`text-[11px] capitalize ${STATUS_STYLES[item.status]}`}>
                                  {item.status}
                                </p>
                              </div>
                            </div>
                          </td>
                        );
                      }
                      if (column.id === 'size') {
                        return (
                          <td key={column.id} className="whitespace-nowrap px-3 py-3 text-slate-300">
                            {formatBytes(item.sizeBytes)}
                          </td>
                        );
                      }
                      if (column.id === 'progress') {
                        return <td key={column.id} className="px-3 py-3"><ProgressCell item={item} /></td>;
                      }
                      if (column.id === 'eta') {
                        return (
                          <td key={column.id} className="hidden whitespace-nowrap px-3 py-3 text-slate-300 xl:table-cell">
                            {formatEta(item.etaSeconds)}
                          </td>
                        );
                      }
                      return (
                        <td key={column.id} className="whitespace-nowrap px-3 py-3 text-slate-400">
                          {item.dateAdded}
                        </td>
                      );
                    })}
                  </motion.tr>
                );
              })}
            </AnimatePresence>
          </tbody>
        </table>

        {items.length === 0 && (
          <div className="flex flex-col items-center justify-center gap-3 px-6 py-20 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-white/10 bg-white/5">
              <Download className="h-7 w-7 text-slate-500" />
            </div>
            <p className="font-medium text-slate-300">No downloads in this view</p>
            <p className="max-w-sm text-sm text-slate-500">
              Add a link from the toolbar or enable clipboard listener to capture copied URLs.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
