import React, { useState, useCallback } from 'react';
import { Cog6ToothIcon, ChevronDownIcon, PlusIcon, CubeIcon } from '@heroicons/react/24/outline';
import { useAppDispatch, useAppSelector } from '../redux/hooks';
import { setCurrentConfig, addSavedConfig } from '../redux/slices/modelConfigSlice';
import { AddModelForm, ModelConfig } from '../forms/AddModelForm';
import { Listbox, ListboxButton, ListboxOption, ListboxOptions } from './ui';
import { providers } from '../configs/providers';

// Provider Logo 组件 - 类似 Continue 的实现
const ProviderIcon: React.FC<{ icon?: string; className?: string }> = ({ icon, className = "h-4 w-4" }) => {
  if (!icon || !icon.endsWith('.png')) {
    return <CubeIcon className={className} />;
  }
  
  return (
    <img 
      src={`logos/${icon}`} 
      alt="" 
      className={`${className} object-contain`}
      onError={(e) => {
        // 如果图片加载失败，隐藏它
        (e.target as HTMLImageElement).style.display = 'none';
      }}
    />
  );
};

interface ModelSelectorProps {
  onModelChange?: (config: ModelConfig) => void;
  compact?: boolean; // 紧凑模式，用于工具栏
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({ onModelChange, compact = false }) => {
  const dispatch = useAppDispatch();
  const { currentConfig, savedConfigs } = useAppSelector(
    (state) => state.modelConfig
  );
  const [showForm, setShowForm] = useState(false);

  // Combine current config with saved configs for the dropdown
  const allConfigs = React.useMemo(() => {
    const configs: ModelConfig[] = [];
    
    // Add saved configs
    savedConfigs.forEach(c => configs.push(c));
    
    // Add current config if not in saved
    if (currentConfig && !savedConfigs.find(c => 
      c.provider === currentConfig.provider && c.model === currentConfig.model
    )) {
      configs.unshift(currentConfig);
    }
    
    // Add default configs from providers if empty
    if (configs.length === 0) {
      Object.values(providers).forEach(provider => {
        if (provider.packages.length > 0) {
          const pkg = provider.packages[0];
          configs.push({
            provider: provider.provider,
            model: pkg.params.model,
            title: pkg.title,
            contextLength: pkg.params.contextLength,
          });
        }
      });
    }
    
    return configs;
  }, [currentConfig, savedConfigs]);

  const handleSelectConfig = useCallback((config: ModelConfig) => {
    dispatch(setCurrentConfig(config));
    onModelChange?.(config);
  }, [dispatch, onModelChange]);

  const handleSaveNewConfig = useCallback((config: ModelConfig) => {
    dispatch(addSavedConfig(config));
    dispatch(setCurrentConfig(config));
    setShowForm(false);
    onModelChange?.(config);
  }, [dispatch, onModelChange]);

  const getProviderIcon = (providerName: string) => {
    const provider = providers[providerName];
    return provider?.icon;
  };

  if (showForm) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <div className="bg-background border border-border rounded-lg shadow-xl max-w-md w-full mx-4 max-h-[80vh] overflow-y-auto">
          <AddModelForm
            onDone={handleSaveNewConfig}
            onCancel={() => setShowForm(false)}
          />
        </div>
      </div>
    );
  }

  // 紧凑模式 - 用于工具栏
  if (compact) {
    return (
      <Listbox
        value={currentConfig || undefined}
        onChange={handleSelectConfig}
      >
        <div className="relative">
          <ListboxButton className="flex items-center gap-1.5 px-1.5 py-0.5 text-xs text-description hover:text-foreground hover:bg-list-hover rounded transition-colors border-0 bg-transparent">
            <ProviderIcon icon={getProviderIcon(currentConfig?.provider || 'openai')} className="h-3.5 w-3.5" />
            <span className="max-w-[100px] truncate">{currentConfig?.title || 'Select'}</span>
            <ChevronDownIcon className="h-3 w-3 opacity-60" />
          </ListboxButton>
          
          <ListboxOptions className="min-w-[200px]">
            <div className="flex items-center justify-between px-2 py-1">
              <span className="text-description text-xs font-medium">Models</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowForm(true);
                }}
                className="p-0.5 rounded hover:bg-list-hover text-description hover:text-foreground"
              >
                <Cog6ToothIcon className="h-3.5 w-3.5" />
              </button>
            </div>
            {allConfigs.map((config, idx) => (
              <ListboxOption key={`${config.provider}-${config.model}-${idx}`} value={config}>
                <span className="flex items-center gap-2">
                  <ProviderIcon icon={getProviderIcon(config.provider)} className="h-3.5 w-3.5" />
                  <span className="truncate">{config.title}</span>
                </span>
              </ListboxOption>
            ))}
            <div className="border-t border-border mt-1">
              <ListboxOption
                value={{ _action: 'add' } as any}
                onClick={(e: React.MouseEvent) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setShowForm(true);
                }}
              >
                <span className="flex items-center gap-2 text-description">
                  <PlusIcon className="h-3.5 w-3.5" />
                  Add Chat model
                </span>
              </ListboxOption>
            </div>
          </ListboxOptions>
        </div>
      </Listbox>
    );
  }

  // 完整模式
  return (
    <div className="flex items-center gap-2">
      <Listbox
        value={currentConfig || undefined}
        onChange={handleSelectConfig}
      >
        <div className="relative flex-1">
          <ListboxButton className="w-full justify-between">
            <span className="flex items-center gap-2">
              <ProviderIcon icon={getProviderIcon(currentConfig?.provider || 'openai')} className="h-4 w-4" />
              <span className="truncate">{currentConfig?.title || 'Select Model'}</span>
            </span>
            <ChevronDownIcon className="h-4 w-4 text-description" />
          </ListboxButton>
          
          <ListboxOptions className="w-full">
            <div className="text-description-muted px-2 py-1 text-xs font-medium">
              Saved Models
            </div>
            {allConfigs.map((config, idx) => (
              <ListboxOption key={`${config.provider}-${config.model}-${idx}`} value={config}>
                <span className="flex items-center gap-2">
                  <ProviderIcon icon={getProviderIcon(config.provider)} className="h-4 w-4" />
                  <span>{config.title}</span>
                </span>
                <span className="text-description-muted text-2xs">
                  {config.provider}
                </span>
              </ListboxOption>
            ))}
            <div className="border-t border-border mt-1 pt-1">
              <ListboxOption
                value={{ _action: 'add' } as any}
                onClick={(e: React.MouseEvent) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setShowForm(true);
                }}
              >
                <span className="flex items-center gap-2 text-description">
                  <PlusIcon className="h-4 w-4" />
                  Add Chat model
                </span>
              </ListboxOption>
            </div>
          </ListboxOptions>
        </div>
      </Listbox>
      
      <button
        onClick={() => setShowForm(true)}
        className="p-1.5 rounded hover:bg-list-hover text-description hover:text-foreground transition-colors"
        title="Configure model"
      >
        <Cog6ToothIcon className="h-4 w-4" />
      </button>
    </div>
  );
};

export default ModelSelector;
