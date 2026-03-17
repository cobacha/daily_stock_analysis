import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Components } from 'react-markdown';

const mdComponents: Components = {
  // h1 (# 🎯 大盘复盘) 已由外层页面标题代替，隐藏避免重复
  h1: () => null,

  // h2 (## 日期 + 标题) — 带分割线的区块标题
  h2: ({ children }) => (
    <div className="flex items-center gap-3 mt-5 mb-2.5 first:mt-0">
      <span className="text-sm font-semibold text-primary whitespace-nowrap">{children}</span>
      <div className="flex-1 h-px bg-white/6 [[data-theme=light]_&]:bg-black/8" />
    </div>
  ),

  // h3 (### 章节) — 青色小标题
  h3: ({ children }) => (
    <h3 className="text-xs font-semibold text-cyan/70 tracking-wide mt-3 mb-1.5">
      {children}
    </h3>
  ),

  // 正文段落
  p: ({ children }) => (
    <p className="text-sm text-secondary-text leading-relaxed">{children}</p>
  ),

  // blockquote — 数据高亮块（涨跌统计、领涨领跌行业等）
  blockquote: ({ children }) => (
    <div className="my-2 rounded-r-lg border-l-2 border-cyan/35 bg-cyan/5 pl-3 pr-3 py-2 [&_p]:text-xs [&_p]:text-secondary-text [&_p]:leading-relaxed">
      {children}
    </div>
  ),

  // 加粗
  strong: ({ children }) => (
    <strong className="font-semibold text-white">{children}</strong>
  ),

  // 斜体（报尾免责声明等）
  em: ({ children }) => (
    <em className="not-italic text-xs text-muted-text">{children}</em>
  ),

  // 无序列表
  ul: ({ children }) => (
    <ul className="my-1.5 space-y-1.5 pl-1">{children}</ul>
  ),

  // 有序列表
  ol: ({ children }) => (
    <ol className="my-1.5 space-y-1.5 pl-1">{children}</ol>
  ),

  // 列表项（ul / ol 统一样式）
  li: ({ children }) => (
    <li className="flex items-start gap-2 text-sm text-secondary-text leading-relaxed">
      <span className="mt-[7px] w-1 h-1 rounded-full bg-cyan/50 shrink-0" />
      <span className="flex-1">{children}</span>
    </li>
  ),

  // 水平分隔线
  hr: () => <div className="h-px bg-white/6 my-3" />,

  // 表格外壳（支持横向滚动）
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto rounded-lg border border-white/8">
      <table className="w-full border-collapse text-xs">{children}</table>
    </div>
  ),

  thead: ({ children }) => (
    <thead className="border-b border-white/8 bg-white/5">{children}</thead>
  ),

  tbody: ({ children }) => (
    <tbody className="divide-y divide-white/5">{children}</tbody>
  ),

  tr: ({ children }) => (
    <tr className="transition-colors hover:bg-white/[0.03]">{children}</tr>
  ),

  th: ({ children }) => (
    <th className="px-3 py-2 text-left text-[11px] font-medium text-muted-text whitespace-nowrap">
      {children}
    </th>
  ),

  td: ({ children }) => (
    <td className="px-3 py-2 text-secondary-text whitespace-nowrap">{children}</td>
  ),

  // 行内代码 / 代码块
  code: ({ className, children }) => {
    const isBlock = !!className;
    return isBlock ? (
      <code className="font-mono text-xs text-secondary-text">{children}</code>
    ) : (
      <code className="rounded bg-white/8 px-1.5 py-0.5 font-mono text-xs text-cyan">
        {children}
      </code>
    );
  },

  pre: ({ children }) => (
    <pre className="my-2 overflow-x-auto rounded-lg border border-white/8 bg-white/5 p-3 font-mono text-xs text-secondary-text">
      {children}
    </pre>
  ),
};

interface Props {
  content: string;
}

export const MarketReviewMarkdown: React.FC<Props> = ({ content }) => (
  <div className="space-y-2">
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
      {content}
    </ReactMarkdown>
  </div>
);
