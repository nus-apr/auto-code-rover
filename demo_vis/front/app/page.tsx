'use client'
import clsx from 'clsx';
import { BsStars } from "react-icons/bs";
import { FaWpforms } from "react-icons/fa6";
import { v4 as uuidv4 } from 'uuid';
import React, { useState, useEffect, useRef } from 'react'
import { FaHandsHelping } from "react-icons/fa";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vs } from "react-syntax-highlighter/dist/esm/styles/prism";
import { PiWheelchair } from "react-icons/pi";
import toast, { Toaster } from 'react-hot-toast';
import { FieldValues, useForm } from 'react-hook-form';
import { FaAnglesDown, FaAnglesUp } from "react-icons/fa6";
import Markdown from 'marked-react';

interface Message {
  id: string
  category: string,
  is_open: boolean,
  // receive_time: Date
};

interface AutoCodeRoverMessage extends Message {
  title: string,
  message: string,
  category: 'auto_code_rover'
};

interface ContextRetrievalAgentMessage extends Message {
  title: string,
  message: string,
  category: 'context_retrieval_agent'
};

interface PatchGenerationMessage extends Message {
  title: string,
  message: string,
  category: 'patch_generation'
};

interface IssueInfo extends Message {
  problem_statement: string,
  category: 'issue_info'
};

type AnyMessage = AutoCodeRoverMessage | ContextRetrievalAgentMessage | IssueInfo | PatchGenerationMessage;

function MarkdownRender({
  markdown,
  baseURL
}: {
  markdown: string,
  baseURL?: string
}) {
  const uuid = uuidv4();
  const renderer = {
    code(snippet: string, lang: string) {
      return <div>
        {/* monoBlue  */}
        <SyntaxHighlighter language={lang} style={vs}>
          {snippet}
        </SyntaxHighlighter>
      </div>
    },
  };
  return (
    <article className='prose'>
      <Markdown
        value={markdown}
        baseURL={baseURL ? baseURL : ''}
        renderer={renderer}
        gfm
      />
    </article >
  )
}

const LoadingDiv = () => {
  return (
    <div
      className='bg-gray-200 bg-opacity-30 p-4 rounded-2xl flex space-x-3
          group hover:bg-slate-200
          '
    >
      <div className="flex-auto py-0.5 text-lg leading-normal text-gray-800">
        <div
          className="font-medium text-gray-900 flex items-center space-x-2 justify-around"
        >
          <span>Wating for more Agent search and actions ... </span>
        </div>
      </div>
    </div>
  );
};

const MessageDiv = ({
  message,
  setIsOpen,
  icon: Icon
}: {
  message: AutoCodeRoverMessage | ContextRetrievalAgentMessage | PatchGenerationMessage,
  setIsOpen: (isOpen: boolean) => void,
  icon: React.ReactNode
}) => {

  return (
    <>
      {
        message.is_open &&
        <div className='bg-gray-200 bg-opacity-30 p-4 pr-12 rounded-2xl flex space-x-3'>
          <div>
            <div className="relative flex h-6 w-6 flex-none items-center justify-center bg-white">
              {Icon}
            </div>
          </div>
          <div className="flex-auto py-0.5 text-lg leading-normal text-gray-800">
            <button
              className="font-medium text-gray-900 flex items-center space-x-2 
                hover:bg-slate-200 px-2 rounded-md
              "
              onClick={() => setIsOpen(false)}
            >
              <span>{message.title}</span>
              <FaAnglesUp className='h-3 w-3' />

            </button>
            <div
              className='mt-2'
            >
              <MarkdownRender markdown={message.message} />
            </div>
          </div>
          {/* <time dateTime='time' className="flex-none py-0.5 text-xs leading-5 text-gray-950">
            time
          </time> */}
        </div>
      }
      {
        !message.is_open &&
        <button
          className='bg-gray-200 bg-opacity-30 p-4 rounded-2xl flex space-x-3
          group hover:bg-slate-200
          '
          onClick={() => setIsOpen(true)}
        >
          <div>
            <div className="relative flex h-6 w-6 flex-none items-center justify-center bg-white">
              {Icon}
            </div>
          </div>
          <div className="flex-auto py-0.5 text-lg leading-normal text-gray-800">
            <div
              className="font-medium text-gray-900 flex items-center space-x-2
              "
            >
              <span>{message.title}</span>
              <FaAnglesDown className='h-3 w-3' />
            </div>
          </div>
          {/* <time dateTime='time' className="flex-none py-0.5 text-xs leading-5 text-gray-950">
          time
        </time> */}
        </button>
      }

    </>
  );
};

export default function App() {

  const {
    register,
    handleSubmit,
    setValue
  } = useForm<FieldValues>();
  const [messages, setMessage] = useState<Array<AnyMessage>>([]);
  const [problemStatement, setProblemStatement] = useState<string | undefined>(undefined);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // state indecating the process: 
  // 0: before starting
  // 1: waiting for servering cloning the git issue
  // 2: communicating with server and show the agent actions
  // 3: done
  const [loadingState, setLoadingState] = useState<number>(0);
  const [toastId, setToastId] = useState<string>();

  const demo_form_callback = () => {
    setValue('repository_link', 'https://github.com/langchain-ai/langchain.git');
    setValue('commit_hash', 'cb6e5e5');
    setValue('issue_link', 'https://github.com/langchain-ai/langchain/issues/20453');
  };

  const clear_form_callback = () => {
    setValue('repository_link', '');
    setValue('commit_hash', '');
    setValue('issue_link', '');
    setLoadingState(0);
    setProblemStatement('');
    setMessage([]);
    toast.dismiss();
  };

  const onsubmmit_callback = async (data: FieldValues) => {
    const call_server = fetch('http://localhost:5000/api/run_github_issue', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    })

    toast.loading('downloading issue and repository ...');

    call_server.then(response => {
      if (response.status !== 200) {
        return response.json().then(data => {
          toast.error(data.message);
          throw new Error(data.message);
        });
      }

      if (!response.body)
        throw Error('???');
      setLoadingState(1);
      const reader = response.body.getReader();

      function read(): Promise<void> {
        return reader.read().then(({ done, value }) => {
          if (done) {
            console.log('Stream completed');
            toast.dismiss();
            toast.success('Done !');
            setLoadingState(0);
            return;
          }
          const text = new TextDecoder().decode(value);
          text.split('</////json_end>').forEach(item => {
            if (item) {
              const message: AnyMessage = JSON.parse(item);
              message.is_open = true;
              message.id = uuidv4();
              console.log(message);
              if (message.category === 'issue_info') {
                setIssueInfo(message);
                setLoadingState(2);
                toast.dismiss();
                toast.success('Git issue clone successfully !');
                toast.loading('Agent running');
              } else {
                setMessage(prevMessages => {
                  const newMessages = prevMessages.map((m, index) => {
                    if (index === prevMessages.length - 1) {
                      return { ...m, is_open: false };
                    } else {
                      return m;
                    }
                  });
                  newMessages.push(message);
                  return newMessages;
                });
              }
            }
          })
          return read();
        });
      }
      return read();
    })
      .catch(error => {
        console.error('Error:', error);
      });
  };

  const setIssueInfo = (message: IssueInfo) => {
    const s = message.problem_statement;
    const newlineIndex = s.indexOf('\n');
    const firstLine = newlineIndex !== -1 ? s.substring(0, newlineIndex) : s;
    const lastLine = newlineIndex !== -1 ? s.substring(newlineIndex + 1) : s;
    // setProblemStatement('## ' + firstLine + ''message.problem_statement);
    setProblemStatement(`## ${firstLine} \n ${lastLine}`)
  }

  const setOpen = (isOpen: boolean, set_message_id: string) => {
    const newItems = messages.map(message__ => {
      if (message__.id === set_message_id) {
        return { ...message__, is_open: isOpen };
      }
      return message__;
    });
    setMessage(newItems);
  };

  return (
    <div className='w-full h-[100vh] flex flex-row'>
      <Toaster
        position="bottom-right"
        reverseOrder={false}
      />

      <div className='
        w-[30%] h-[100vh] lg:p-6 flex flex-col space-y-3
        bg-gray-100
      '>

        <label className='text-2xl'>
          Input the meta infomation of issue here
        </label>

        <form
          className='flex flex-col space-y-3'>

          <div className='flex items-center space-x-3'>
            <label className='w-32'>
              repository
            </label>
            <input
              {...register('repository_link')}
              type="text"
              className='p-2 border w-[80%] rounded-sm'
              placeholder='the link to the repository'
            />
          </div>

          <div className='flex items-center space-x-3'>
            <label className='w-32'>
              commit hash
            </label>
            <input
              {...register('commit_hash')}
              type="text"
              className='p-2 border w-[80%] rounded-sm'
              placeholder='the commit hash to checkout'
            />
          </div>

          <div className='flex items-center space-x-3'>
            <label className='w-32'>
              issue
            </label>
            <input
              {...register('issue_link')}
              type="text"
              className='p-2 border w-[80%] rounded-sm'
              placeholder='The link to the issue'
            />
          </div>

          <div className='flex justify-around text-sm'>

            <button
              className='w-[40%] m-1 py-4 p-2 border rounded-xl bg-slate-200 hover:bg-slate-300 hover:border-slate-50'
              onClick={(event: React.MouseEvent) => {
                event.preventDefault();
                clear_form_callback();
              }}>
              🧹 Clear all ! 🧹
            </button>

            <button
              className='w-[40%] m-1 py-4 p-2 border rounded-xl bg-slate-200 hover:bg-slate-300 hover:border-slate-50'
              type='submit'
              onClick={handleSubmit(onsubmmit_callback)}>
              🚀 Boot Now ! 🚀
            </button>
          </div>
        </form>

        <div className={clsx(
          'py-2 overflow-y-auto border-2 border-t-2 border-gray-400 border-t-gray-400 rounded-xl border-dashed w-full h-full',
          !problemStatement && 'flex items-center justify-around'
        )}>
          {
            !problemStatement && (
              <div className='flex flex-col items-center space-y-2'>
                <FaWpforms className='w-20 h-20' />
                <span className='font-semibold'>No Issues</span>
                <span className='text-gray-500'>
                  Try one example we prepare for you.
                </span>
                <button
                  className='m-1 py-4 p-2 border rounded-xl bg-slate-200 hover:bg-slate-300 hover:border-slate-50'
                  onClick={(event: React.MouseEvent) => {
                    event.preventDefault();
                    demo_form_callback();
                  }}>
                  💡 Try example ? 💡
                </button>
              </div>
            )
          }
          {
            problemStatement && (
              <div className='p-4 py-2'>
                <MarkdownRender
                  markdown={problemStatement}
                >
                </MarkdownRender>
              </div>
            )
          }
        </div>
      </div>

      <div className='w-[70%] h-[100vh] overflow-y-auto'>
        <ul
          role="list"
          className="
      space-y-6
      p-6
      "
        >
          {messages.map((message, index) => (
            <li key={message.id} className="relative flex gap-x-4 overflow-x-auto">
              {
                !(message.category === 'issue_info') &&
                <MessageDiv
                  message={message as AutoCodeRoverMessage | ContextRetrievalAgentMessage | PatchGenerationMessage}
                  setIsOpen={(isopen: boolean) => setOpen(isopen, message.id)}
                  icon={
                    <>
                      {
                        message.category === 'auto_code_rover' && (
                          <FaHandsHelping className='h-6 w-6 text-indigo-600 bg-gray-200 bg-opacity-30'
                            aria-hidden="true"
                          />
                        )
                      }
                      {
                        message.category === 'context_retrieval_agent' && (

                          <PiWheelchair className='h-6 w-6 text-indigo-600 bg-gray-200 bg-opacity-30'
                            aria-hidden="true"
                          />
                        )
                      }
                      {
                        message.category === 'patch_generation' && (
                          <BsStars className='h-6 w-6 text-indigo-600 bg-gray-200 bg-opacity-30'
                            aria-hidden="true"
                          />
                        )
                      }
                    </>
                  }
                />
              }

            </li>
          ))}
          {
            loadingState === 1 &&
            <div ref={messagesEndRef}>
              <LoadingDiv />
            </div>
          }
        </ul>
      </div>
    </div >
  )
}
