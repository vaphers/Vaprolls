import React, { useState } from 'react';
import { useCrawlStore } from '../../store/useCrawlStore';
import type { CustomExtractorRule, CustomSearchRule } from '../../types';
import { Code, Search, Plus, Trash2, X } from 'lucide-react';

export const CustomRulesModal: React.FC = () => {
  const {
    isCustomRulesOpen,
    setIsCustomRulesOpen,
    customExtractors,
    setCustomExtractors,
    customSearchRules,
    setCustomSearchRules,
  } = useCrawlStore();

  const [activeTab, setActiveTab] = useState<'extractors' | 'search'>('extractors');

  // Extraction draft
  const [extName, setExtName] = useState('');
  const [extType, setExtType] = useState<'xpath' | 'css' | 'regex'>('xpath');
  const [extExpression, setExtExpression] = useState('');
  const [extAttribute, setExtAttribute] = useState('');

  // Search draft
  const [srchName, setSrchName] = useState('');
  const [srchType, setSrchType] = useState<'contains' | 'does_not_contain' | 'regex'>('contains');
  const [srchQuery, setSrchQuery] = useState('');

  if (!isCustomRulesOpen) return null;

  const handleAddExtractor = () => {
    if (!extName.trim() || !extExpression.trim()) {
      alert("Please provide both a Rule Name and an Expression.");
      return;
    }
    const newRule: CustomExtractorRule = {
      name: extName.trim(),
      type: extType,
      expression: extExpression.trim(),
      extract_attribute: extAttribute.trim() || undefined,
    };
    setCustomExtractors([...customExtractors, newRule]);
    setExtName('');
    setExtExpression('');
    setExtAttribute('');
  };

  const handleRemoveExtractor = (idx: number) => {
    setCustomExtractors(customExtractors.filter((_, i) => i !== idx));
  };

  const handleAddSearch = () => {
    if (!srchName.trim() || !srchQuery.trim()) {
      alert("Please provide both a Rule Name and a Query String.");
      return;
    }
    const newRule: CustomSearchRule = {
      name: srchName.trim(),
      type: srchType,
      query: srchQuery.trim(),
    };
    setCustomSearchRules([...customSearchRules, newRule]);
    setSrchName('');
    setSrchQuery('');
  };

  const handleRemoveSearch = (idx: number) => {
    setCustomSearchRules(customSearchRules.filter((_, i) => i !== idx));
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white border-2 border-[#C8B670] shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden text-black">
        {/* Header */}
        <div className="bg-[#FFE08A] border-b border-[#C8B670] px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Code className="w-5 h-5 text-black" />
            <h2 className="font-bold text-sm text-black">Custom Extraction & Custom Search</h2>
          </div>
          <button
            onClick={() => setIsCustomRulesOpen(false)}
            className="p-1 hover:bg-[#FFF7D6] text-black font-bold"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Buttons */}
        <div className="flex items-center border-b border-[#E2D5A0] bg-[#FFF7D6] px-3 text-xs">
          <button
            onClick={() => setActiveTab('extractors')}
            className={`px-4 py-2 font-bold border-b-2 flex items-center gap-1.5 transition-colors ${
              activeTab === 'extractors' ? 'border-b-black bg-white text-black' : 'border-b-transparent text-gray-600'
            }`}
          >
            <Code className="w-3.5 h-3.5" />
            Custom Extraction ({customExtractors.length})
          </button>
          <button
            onClick={() => setActiveTab('search')}
            className={`px-4 py-2 font-bold border-b-2 flex items-center gap-1.5 transition-colors ${
              activeTab === 'search' ? 'border-b-black bg-white text-black' : 'border-b-transparent text-gray-600'
            }`}
          >
            <Search className="w-3.5 h-3.5" />
            Custom Search ({customSearchRules.length})
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-auto p-4 space-y-4 text-xs bg-white">
          {activeTab === 'extractors' ? (
            <div className="space-y-4">
              <div className="p-3 bg-[#FFF7D6]/40 border border-[#C8B670] rounded-none space-y-2">
                <span className="font-bold text-xs flex items-center gap-1 text-black">
                  <Plus className="w-4 h-4 text-black" /> Add Extraction Rule
                </span>
                <p className="text-[11px] text-gray-600">
                  Extract custom data points from HTML DOM using XPath, CSS selectors, or Regular Expressions during the crawl.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-2 pt-1">
                  <div>
                    <label className="text-[10px] uppercase font-bold text-gray-600 block mb-0.5">Name</label>
                    <input
                      type="text"
                      placeholder="e.g. Product_Price"
                      value={extName}
                      onChange={(e) => setExtName(e.target.value)}
                      className="w-full border border-[#C8B670] px-2 py-1 font-mono text-xs outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] uppercase font-bold text-gray-600 block mb-0.5">Selector Type</label>
                    <select
                      value={extType}
                      onChange={(e) => setExtType(e.target.value as any)}
                      className="w-full border border-[#C8B670] px-2 py-1 text-xs outline-none bg-white"
                    >
                      <option value="xpath">XPath</option>
                      <option value="css">CSS Selector</option>
                      <option value="regex">Regular Expression</option>
                    </select>
                  </div>
                  <div className="md:col-span-2">
                    <label className="text-[10px] uppercase font-bold text-gray-600 block mb-0.5">Expression</label>
                    <input
                      type="text"
                      placeholder={
                        extType === 'xpath'
                          ? "//span[@class='price']"
                          : extType === 'css'
                          ? ".price, [data-price]"
                          : "GTM-[A-Z0-9]+"
                      }
                      value={extExpression}
                      onChange={(e) => setExtExpression(e.target.value)}
                      className="w-full border border-[#C8B670] px-2 py-1 font-mono text-xs outline-none"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1">
                  <div className="flex items-center gap-2">
                    <label className="text-[10px] uppercase font-bold text-gray-600">Attribute (Optional):</label>
                    <input
                      type="text"
                      placeholder="e.g. content, href, data-id"
                      value={extAttribute}
                      onChange={(e) => setExtAttribute(e.target.value)}
                      className="border border-[#C8B670] px-2 py-0.5 font-mono text-xs outline-none w-48"
                    />
                  </div>
                  <button
                    onClick={handleAddExtractor}
                    className="px-3 py-1 bg-black text-white font-bold hover:bg-neutral-800 transition-colors flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add Rule
                  </button>
                </div>
              </div>

              {/* Existing Rules List */}
              <div className="space-y-2">
                <span className="font-bold text-xs uppercase text-gray-700 block">Active Extraction Rules</span>
                {customExtractors.length === 0 ? (
                  <div className="text-gray-400 py-6 text-center border border-dashed border-[#C8B670]">
                    No custom extraction rules configured yet.
                  </div>
                ) : (
                  <table className="w-full text-left border-collapse font-mono text-xs">
                    <thead>
                      <tr className="bg-[#FFF7D6] border-b border-[#C8B670] font-bold">
                        <th className="p-2 border-r border-[#C8B670] w-36">Name</th>
                        <th className="p-2 border-r border-[#C8B670] w-24">Type</th>
                        <th className="p-2 border-r border-[#C8B670]">Expression</th>
                        <th className="p-2 border-r border-[#C8B670] w-28">Attribute</th>
                        <th className="p-2 w-12 text-center">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E2D5A0]">
                      {customExtractors.map((rule, idx) => (
                        <tr key={idx} className="hover:bg-[#FFF7D6]">
                          <td className="p-2 border-r border-[#E2D5A0] font-bold font-sans">{rule.name}</td>
                          <td className="p-2 border-r border-[#E2D5A0] uppercase text-[11px] font-sans">{rule.type}</td>
                          <td className="p-2 border-r border-[#E2D5A0] break-all">{rule.expression}</td>
                          <td className="p-2 border-r border-[#E2D5A0]">{rule.extract_attribute || 'Inner Text'}</td>
                          <td className="p-2 text-center">
                            <button
                              onClick={() => handleRemoveExtractor(idx)}
                              className="text-gray-400 hover:text-[#b91c1c]"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-3 bg-[#FFF7D6]/40 border border-[#C8B670] rounded-none space-y-2">
                <span className="font-bold text-xs flex items-center gap-1 text-black">
                  <Plus className="w-4 h-4 text-black" /> Add Search Rule
                </span>
                <p className="text-[11px] text-gray-600">
                  Search raw HTML for specific tracking scripts, keywords, or missing tags (e.g. Contains "UA-" or Does Not Contain "dataLayer").
                </p>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-2 pt-1">
                  <div>
                    <label className="text-[10px] uppercase font-bold text-gray-600 block mb-0.5">Rule Name</label>
                    <input
                      type="text"
                      placeholder="e.g. Has_GTM_Script"
                      value={srchName}
                      onChange={(e) => setSrchName(e.target.value)}
                      className="w-full border border-[#C8B670] px-2 py-1 font-mono text-xs outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] uppercase font-bold text-gray-600 block mb-0.5">Condition</label>
                    <select
                      value={srchType}
                      onChange={(e) => setSrchType(e.target.value as any)}
                      className="w-full border border-[#C8B670] px-2 py-1 text-xs outline-none bg-white"
                    >
                      <option value="contains">Contains</option>
                      <option value="does_not_contain">Does Not Contain</option>
                      <option value="regex">Matches Regex</option>
                    </select>
                  </div>
                  <div className="md:col-span-2">
                    <label className="text-[10px] uppercase font-bold text-gray-600 block mb-0.5">Query String / Pattern</label>
                    <input
                      type="text"
                      placeholder="googletagmanager.com/gtm.js"
                      value={srchQuery}
                      onChange={(e) => setSrchQuery(e.target.value)}
                      className="w-full border border-[#C8B670] px-2 py-1 font-mono text-xs outline-none"
                    />
                  </div>
                </div>

                <div className="flex justify-end pt-1">
                  <button
                    onClick={handleAddSearch}
                    className="px-3 py-1 bg-black text-white font-bold hover:bg-neutral-800 transition-colors flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add Search Rule
                  </button>
                </div>
              </div>

              {/* Active Search Rules */}
              <div className="space-y-2">
                <span className="font-bold text-xs uppercase text-gray-700 block">Active Custom Search Rules</span>
                {customSearchRules.length === 0 ? (
                  <div className="text-gray-400 py-6 text-center border border-dashed border-[#C8B670]">
                    No custom search rules configured yet.
                  </div>
                ) : (
                  <table className="w-full text-left border-collapse font-mono text-xs">
                    <thead>
                      <tr className="bg-[#FFF7D6] border-b border-[#C8B670] font-bold">
                        <th className="p-2 border-r border-[#C8B670] w-48">Rule Name</th>
                        <th className="p-2 border-r border-[#C8B670] w-36">Condition</th>
                        <th className="p-2 border-r border-[#C8B670]">Query / Pattern</th>
                        <th className="p-2 w-12 text-center">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E2D5A0]">
                      {customSearchRules.map((rule, idx) => (
                        <tr key={idx} className="hover:bg-[#FFF7D6]">
                          <td className="p-2 border-r border-[#E2D5A0] font-bold font-sans">{rule.name}</td>
                          <td className="p-2 border-r border-[#E2D5A0] uppercase text-[11px] font-sans">
                            {rule.type.replace('_', ' ')}
                          </td>
                          <td className="p-2 border-r border-[#E2D5A0] break-all">{rule.query}</td>
                          <td className="p-2 text-center">
                            <button
                              onClick={() => handleRemoveSearch(idx)}
                              className="text-gray-400 hover:text-[#b91c1c]"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-[#FFF7D6] px-4 py-2 border-t border-[#C8B670] flex items-center justify-between">
          <span className="text-[11px] text-gray-500">
            Rules apply automatically on subsequent crawls and populate the <strong>Custom Extraction</strong> & <strong>Custom Search</strong> tabs.
          </span>
          <button
            onClick={() => setIsCustomRulesOpen(false)}
            className="px-4 py-1.5 bg-black text-white font-bold text-xs hover:bg-neutral-800 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
