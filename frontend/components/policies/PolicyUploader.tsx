'use client';

import { useState } from 'react';
import { FileUpload, Input, Button, ErrorMessage } from '@/components/ui';
import { uploadPolicy } from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';
import { PolicyUploadResponse } from '@/lib/types';
import type { EvidenceSection } from '@/lib/types';

interface PolicyUploaderProps {
  assessmentId: string;
  onUploadComplete: (response: PolicyUploadResponse) => void;
  section: EvidenceSection;
}

const SECTION_CONFIG: Record<EvidenceSection, { accept: string; helperText: string; label: string }> = {
  policy:    { accept: '.pdf,.docx,.doc,.txt,.md',                  helperText: 'PDF, DOCX, TXT, or Markdown',                   label: 'Upload Policy Document' },
  process:   { accept: '.pdf,.docx,.doc,.txt,.md',                  helperText: 'PDF, DOCX, TXT, or Markdown',                   label: 'Upload Process Document' },
  control:   { accept: '.csv,.xlsx,.xls',                           helperText: 'CSV or Excel spreadsheet',                      label: 'Upload Controls Spreadsheet' },
  interview: { accept: '.docx,.doc,.txt,.md',                       helperText: 'DOCX, TXT, or Markdown',                        label: 'Upload Interview Document' },
  proof:     { accept: '.pdf,.docx,.doc,.txt,.md,.xlsx,.xls,.csv',  helperText: 'PDF, DOCX, TXT, Markdown, or Excel/CSV',        label: 'Upload Proof Document' },
};

export function PolicyUploader({ assessmentId, onUploadComplete, section }: PolicyUploaderProps) {
  const userId = useUserId();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [metadata, setMetadata] = useState({ name: '', description: '', version: '', owner: '' });

  const config = SECTION_CONFIG[section];

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    if (!metadata.name) {
      setMetadata({ ...metadata, name: file.name.replace(/\.[^/.]+$/, '') });
    }
  };

  const handleUpload = async () => {
    if (!userId || !selectedFile) return;
    setUploading(true);
    setError(null);
    try {
      const response = await uploadPolicy(assessmentId, selectedFile, { ...metadata, section }, userId);
      onUploadComplete(response);
      setSelectedFile(null);
      setMetadata({ name: '', description: '', version: '', owner: '' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <FileUpload
        accept={config.accept}
        onFileSelect={handleFileSelect}
        uploading={uploading}
        label={config.label}
        helperText={config.helperText}
      />

      {selectedFile && (
        <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600">
            Selected file: <span className="font-medium">{selectedFile.name}</span>
          </p>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Name"
              value={metadata.name}
              onChange={(e) => setMetadata({ ...metadata, name: e.target.value })}
              placeholder="Document name"
            />
            <Input
              label="Version"
              value={metadata.version}
              onChange={(e) => setMetadata({ ...metadata, version: e.target.value })}
              placeholder="1.0"
            />
            <Input
              label="Owner"
              value={metadata.owner}
              onChange={(e) => setMetadata({ ...metadata, owner: e.target.value })}
              placeholder="Team or person"
            />
            <Input
              label="Description"
              value={metadata.description}
              onChange={(e) => setMetadata({ ...metadata, description: e.target.value })}
              placeholder="Brief description..."
            />
          </div>
          <div className="flex justify-end">
            <Button onClick={handleUpload} loading={uploading}>
              Upload
            </Button>
          </div>
        </div>
      )}

      {error && <ErrorMessage message={error} />}
    </div>
  );
}
